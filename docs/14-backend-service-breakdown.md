# Backend Service Breakdown

## 1. FastAPI Routers & Endpoints

| Router | Method | Path | Purpose |
|---|---|---|---|
| **Auth** | POST | `/api/auth/login` | Authenticate and return JWT token |
| | POST | `/api/auth/logout` | Invalidate session/token |
| **Users** | GET | `/api/users/me` | Return profile and role info |
| | PUT | `/api/users/me/password` | Update password |
| **Repositories** | GET | `/api/repositories` | List repos for current user |
| | POST | `/api/repositories` | Register a new GitHub repository |
| | GET | `/api/repositories/{id}` | Get repo metadata and latest scan info |
| | DELETE | `/api/repositories/{id}` | Remove repo from tracking |
| **Scans** | GET | `/api/scans` | List scan history |
| | POST | `/api/scans` | Trigger a new scan for a `repo_id` |
| | GET | `/api/scans/{id}` | Get scan summary |
| | GET | `/api/scans/{id}/status` | Get scan progress/stage |
| **Findings** | GET | `/api/findings` | Query findings (filter by `repo_id`, `scan_id`) |
| | GET | `/api/findings/{id}` | Get finding details + evidence |
| | PATCH | `/api/findings/{id}` | Update review status (e.g. False Positive) |
| **Reports** | GET | `/api/reports` | List generated reports |
| | POST | `/api/reports/export` | Generate PDF for a `scan_id` |
| **Dashboard** | GET | `/api/dashboard/metrics` | Aggregate counts (criticals, top repos) |
| **GitHub** | GET | `/api/github/validate` | Verify PAT/App token connectivity |

## 2. Implied Pydantic Models

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str

class RepositoryCreate(BaseModel):
    url: HttpUrl

class RepositoryResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    language: str | None
    branch: str
    visibility: str

class ScanTrigger(BaseModel):
    repo_id: UUID

class ScanResponse(BaseModel):
    id: UUID
    repo_id: UUID
    status: str
    stage: int
    progress: int
    started_at: datetime | None

class FindingUpdate(BaseModel):
    status: str
    reviewNote: str | None

class FindingResponse(BaseModel):
    id: UUID
    scan_id: UUID
    title: str
    category: str
    severity: str
    confidence: str
    file: str
    line: int | None
    scanner: str
    rule: str
    description: str
    evidence: str | None
    remediation: str | None
    status: str
```

## 3. Celery Task Pipeline

**Orchestration Task (`tasks.run_scan`)**:
- Triggered by POST `/api/scans`.
- Orchestrates the DAG of subtasks.
- Updates Postgres `scan.status` and `scan.stage`.

**Subtasks**:
1. `tasks.clone_repository(repo_url, scan_id)` -> Path to local workspace.
2. Parallel Execution (using Celery `group`):
   - `tasks.scan_secrets(workspace_path)` -> raw findings.
   - `tasks.scan_code(workspace_path)` -> raw findings.
   - `tasks.scan_dependencies(workspace_path)` -> raw findings.
   - `tasks.scan_config(workspace_path)` -> raw findings.
3. `tasks.normalize_findings(raw_results, scan_id)` -> Maps to DB and inserts.
4. `tasks.generate_report(scan_id)` -> Generates PDF cache if requested.
5. `tasks.cleanup_workspace(workspace_path)` -> Guaranteed to run via Celery `finally`/callbacks.

**Resilience (NFR-03, NFR-04)**:
- Soft Time limits applied to scanner tasks (e.g., 10 minutes) to prevent runaways.
- Parallel scanner tasks must not `fail_fast`; if one fails, others must complete. 
- Maximum 3 retries for transient clone network errors; 0 retries for static analysis execution failures.

## 4. Normalized Finding Schema

All 4 scanners must output to this Python dict/Pydantic model in the `normalize_findings` task:
```python
class NormalizedFinding(BaseModel):
    title: str
    category: Literal["Code", "Secrets", "Dependencies", "Configuration"]
    severity: Literal["Critical", "High", "Medium", "Low"]
    confidence: Literal["High", "Medium", "Low"]
    file: str
    line: int | None
    scanner: Literal["Gitleaks", "Semgrep", "Trivy", "Checkov"]
    rule: str
    description: str
    evidence: str | None
    remediation: str | None
```

## 5. Redis Usage & Real-time Progress

- **Queue**: Redis acts as the Celery broker to decouple FastAPI from long-running scans.
- **Progress Tracking**: Scan stage updates (1-10) are written to Redis keys (`scan:progress:{id}`) by the Celery tasks.
- **UI Consumption**: The UI currently polls (or fakes polling) progress. The FastAPI `/api/scans/{id}/status` endpoint will fetch from Redis for fast polling. (Optionally upgrade to Server-Sent Events (SSE) `/api/scans/{id}/stream` if real-time push is required).

## 6. Sandbox / Isolation Options (NFR-01)

Repository content is untrusted. We need to isolate the Celery worker during `tasks.run_scan`.

| Option | Pros | Cons |
|---|---|---|
| **Docker-in-Docker (DinD)** | Spin up an ephemeral container for the scan step. Very clean isolation. | Requires privileged mode on the worker node; complex volume mounting. |
| **gVisor / Kata Containers** | Secure, lightweight VM boundary. Strongest defense against RCE in repo. | Slower startup times; requires specific host infrastructure support. |
| **Unprivileged Unix Users / Cgroups** | Fast, relies on OS level `ulimit` and permissions. | Weak isolation. Untrusted code (e.g. via malicious package manifests during Trivy scanning) could escape or read worker env vars. |

*Note: Final decision depends on deployment infrastructure capabilities (AWS ECS, EKS, bare metal).*
