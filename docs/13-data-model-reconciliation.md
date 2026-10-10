# Data Model Reconciliation

## Field-by-Field Comparison

| Entity.field | In SRS? | In UI? | Proposed Type | Proposed SQLAlchemy column type | Nullable | Notes |
|---|---|---|---|---|---|---|
| **User.id** | Yes | Yes (implicit) | UUID | `UUID(as_uuid=True)` | No | PK |
| **User.email** | No | Yes | String | `String(255)` | No | Needed for auth / UI profile |
| **User.name** | No | Yes | String | `String(255)` | No | UI profile display |
| **User.role** | Yes | Yes | Enum | `String(50)` | No | E.g. Admin, Developer |
| **User.auth_info** | Yes | No | JSON/String | `String(255)` | No | Hashed password or OAuth ID |
| **Repository.id** | Yes | Yes | UUID | `UUID(as_uuid=True)` | No | PK |
| **Repository.url** | Yes | Yes | String | `String(2048)` | No | Git clone URL |
| **Repository.owner_id** | Yes | No | FK | `UUID` | No | Tenancy / FR-10 Access Control |
| **Repository.name** | No | Yes | String | `String(255)` | No | org/repo format in UI |
| **Repository.description** | No | Yes | String | `Text` | Yes | From GitHub metadata |
| **Repository.language** | No | Yes | String | `String(50)` | Yes | From GitHub metadata |
| **Repository.branch** | No | Yes | String | `String(255)` | No | Default branch |
| **Repository.visibility** | No | Yes | String | `String(50)` | No | Public/Private |
| **Scan.id** | Yes | Yes | UUID | `UUID(as_uuid=True)` | No | PK |
| **Scan.repository_id** | Yes | Yes | FK | `UUID` | No | Links to Repository |
| **Scan.status** | Yes | Yes | Enum | `String(50)` | No | Queued, Running, Completed, Failed |
| **Scan.started_at** | Yes | Yes | DateTime | `DateTime(timezone=True)` | Yes | |
| **Scan.completed_at** | No | Yes | DateTime | `DateTime(timezone=True)` | Yes | Needed for duration calc |
| **Scan.commit_sha** | No | Yes | String | `String(40)` | Yes | UI shows scanned commit |
| **Scan.stage** | No | Yes | Integer | `Integer` | No | UI 10-stage loader support |
| **Finding.id** | Yes | Yes | UUID | `UUID(as_uuid=True)` | No | PK |
| **Finding.scan_id** | Yes | Yes | FK | `UUID` | No | The scan that found this |
| **Finding.repository_id** | No | Yes | FK | `UUID` | No | Denormalized for easy querying |
| **Finding.title** | No | Yes | String | `String(255)` | No | |
| **Finding.category** | Yes | Yes | Enum | `String(50)` | No | Code, Secrets, Dependencies, Config |
| **Finding.severity** | Yes | Yes | Enum | `String(50)` | No | Critical, High, Medium, Low |
| **Finding.confidence** | Yes | Yes | Enum | `String(50)` | No | High, Medium, Low |
| **Finding.file_path** | Yes | Yes | String | `String(1024)` | No | Location |
| **Finding.line_number** | Yes | Yes | Integer | `Integer` | Yes | Location (some tools omit line) |
| **Finding.scanner** | No | Yes | String | `String(100)` | No | Gitleaks, Semgrep, Trivy, Checkov |
| **Finding.rule_id** | No | Yes | String | `String(255)` | No | e.g. CVE-2021-1234 |
| **Finding.description** | No | Yes | String | `Text` | No | |
| **Finding.evidence** | Yes | Yes | String | `Text` | Yes | |
| **Finding.remediation** | Yes | Yes | String | `Text` | Yes | Recommendation |
| **Finding.status** | No | Yes | Enum | `String(50)` | No | Open, Reviewed, Resolved, False Positive |
| **Finding.ai_state** | No | Yes | String | `String(50)` | Yes | |
| **Finding.context** | No | Yes | JSON | `JSONB` | Yes | Correlated findings/context |

## Proposed PostgreSQL Tables & Relationships

1. **`users`**: PK `id`. Stores user auth and role.
2. **`repositories`**: PK `id`, FK `owner_id` -> `users.id`. Enforces multi-tenancy.
3. **`scans`**: PK `id`, FK `repository_id` -> `repositories.id`.
4. **`findings`**: PK `id`, FK `scan_id` -> `scans.id`, FK `repository_id` -> `repositories.id`.
5. **`reports`**: PK `id`, FK `scan_id` -> `scans.id`. Stores S3/URL to PDF.

*Note on Tenancy (FR-10)*: Every endpoint must join against `repositories.owner_id` (or a `user_repositories` mapping table if multiple users share a repo) to ensure users only see their own data.

## Proposed Alembic Migration Order

1. `001_create_users_table` (UUID, email, name, password_hash, role)
2. `002_create_repositories_table` (UUID, owner_id FK, url, name, metadata)
3. `003_create_scans_table` (UUID, repository_id FK, status, timestamps, commit_sha, stage)
4. `004_create_findings_table` (UUID, scan_id FK, repo_id FK, category, severity, file, line, scanner, rule, evidence, remediation, status)
5. `005_create_reports_table` (UUID, scan_id FK, pdf_url, created_at)
6. `006_add_indexes` (Index `findings` on `scan_id`, `repo_id`, and `severity` for UI filtering)
