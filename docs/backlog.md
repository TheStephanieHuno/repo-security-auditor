# Product Backlog & User Stories Specification
 
**SRS Reference:** System Requirements Specification   

---

## 1. Traceability Matrix: SRS to User Stories

| SRS Ref | Requirement Name | Associated User Stories |
|---|---|---|
| **FR-01** | User Authentication | US-01, US-02, US-03 |
| **FR-02** | Repository Submission | US-04, US-05 |
| **FR-03** | Repository Validation | US-06, US-07 |
| **FR-04** | Security Scan Engine | US-08, US-09, US-10, US-11, US-12 |
| **FR-05** | Scan Status & Lifecycle | US-13, US-14, US-15 |
| **FR-06** | Findings & Vulnerability Evidence | US-16, US-17, US-18 |
| **FR-07** | Finding Review & Triage | US-19, US-20 |
| **FR-08** | Security Report Generation | US-21, US-22, US-23 |
| **FR-09** | Scan History & Dashboard | US-24, US-25 |
| **FR-10** | Access Control & Tenant Isolation | US-26, US-27 |
| **NFR-01** | Isolated Analysis & Security | US-28 |
| **NFR-02** | Asynchronous Non-Blocking Processing | US-29 |
| **NFR-03** | Check Failure Resilience | US-30 |
| **NFR-04** | Resource Limits & Timeouts | US-31 |
| **NFR-05** | Extensibility & Pluggable Architecture | US-32 |
| **NFR-06** | Usability & Developer Guidance | US-33 |

---

## 2. Product Epics (Core Project Domains)

The backlog is organized into 5 functional Epics:
1. **Epic 1: Authentication, User Roles & Access Control** (FR-01, FR-10)
2. **Epic 2: Repository Management & GitHub Integration** (FR-02, FR-03)
3. **Epic 3: Security Scanner Engine & Isolated Workspaces** (FR-04, FR-05, NFR-01 to NFR-05)
4. **Epic 4: AI Explanations, Findings & PDF Reports** (FR-06, FR-07, FR-08, NFR-06)
5. **Epic 5: Dashboard, History & Platform Delivery** (FR-09, Acceptance Criteria)

---

## 3. User Stories Specification (Sprint 2 MVP — P0 Priority)

---

### Epic 1: Authentication, User Roles & Access Control

#### US-01: User Registration
* **Story:** As a new developer, I want to create an account with my name, email, and password so that I can access the security platform.
* **SRS:** FR-01
* **Story Points:** 2
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-07b, RSA-30
* **Acceptance Criteria:**
  - Password must be hashed using `bcrypt` (cost factor >= 12).
  - Successful registration returns HTTP `201 Created` with a valid JWT token.
  - Duplicate email registrations return HTTP `409 Conflict`.

#### US-02: User Authentication & Token Issuance
* **Story:** As a registered user, I want to sign in with my email and password so that I can receive an authenticated session token.
* **SRS:** FR-01
* **Story Points:** 2
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-05, RSA-28
* **Acceptance Criteria:**
  - Valid credentials return HTTP `200 OK` with a signed JWT token valid for 24 hours.
  - Invalid email or password returns generic HTTP `401 Unauthorized` without revealing which field was incorrect.
  - OAuth2 password flow endpoint (`/api/auth/token`) is available for API clients and Swagger UI.

#### US-03: User Role Management
* **Story:** As an administrator, I want user accounts to store explicit role designations (Developer, Security Analyst, Administrator) so that the system can enforce role-based permissions.
* **SRS:** FR-01, Data Requirements
* **Story Points:** 1
* **Priority:** P0 (High)
* **Technical Tasks:** T-04, RSA-30
* **Acceptance Criteria:**
  - `User` model persists a `role` attribute with default value `developer`.
  - Profile queries (`GET /api/users/me`) serialize the user's role.

#### US-26: Resource Ownership & Data Isolation
* **Story:** As a user, I want my repositories, scans, findings, and reports to be strictly isolated so that other users cannot view or manipulate my data (IDOR Protection).
* **SRS:** FR-10
* **Story Points:** 3
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-06, RSA-29
* **Acceptance Criteria:**
  - All database queries for repositories, scans, and reports enforce `WHERE added_by = current_user.id`.
  - Unauthorized access attempts to another user's resource return HTTP `404 Not Found`.

---

### Epic 2: Repository Management & GitHub Integration

#### US-04: Repository Submission
* **Story:** As a developer, I want to submit a public GitHub repository URL so that the platform can track and analyze my codebase.
* **SRS:** FR-02
* **Story Points:** 2
* **Priority:** P0 (High)
* **Technical Tasks:** T-12, RSA-39
* **Acceptance Criteria:**
  - Submitting a valid URL saves repository metadata to the database under the authenticated user.
  - Submitting an already tracked repository URL returns HTTP `409 Conflict`.

#### US-06: Pre-Flight Repository Validation
* **Story:** As a developer, I want the system to verify that my GitHub repository exists and is accessible before adding it so that I do not trigger broken scans.
* **SRS:** FR-03
* **Story Points:** 3
* **Priority:** P0 (High)
* **Technical Tasks:** T-09, T-10, RSA-37, RSA-38
* **Acceptance Criteria:**
  - `POST /api/repositories/validate` queries GitHub REST API live.
  - Inaccessible or non-existent repositories return HTTP `400 Bad Request`.
  - Valid repositories return repository name, owner, and default branch.

#### US-07: Branch Inspection
* **Story:** As a developer, I want to view all active branches for a repository so that I can choose the specific branch I intend to scan.
* **SRS:** FR-04
* **Story Points:** 2
* **Priority:** P0 (High)
* **Technical Tasks:** T-11, T-11a
* **Acceptance Criteria:**
  - `GET /api/repositories/{id}/branches` returns a list of branch names from GitHub.
  - The repository's default branch is explicitly flagged (`isDefault: true`).
  - Latest 7-character commit SHA is returned for each branch.

---

### Epic 3: Security Scanner Engine & Isolated Workspaces

#### US-08: Scan Dispatch & Initiation
* **Story:** As a developer, I want to initiate a security audit on a chosen branch so that security checks are executed asynchronously without blocking the user interface.
* **SRS:** FR-04, NFR-02
* **Story Points:** 3
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-15, T-24, RSA-45, RSA-48
* **Acceptance Criteria:**
  - `POST /api/scans` creates a new scan in database with initial status `queued` and returns HTTP `201 Created`.
  - The scan job is dispatched to the asynchronous background worker queue.

#### US-28: Isolated Workspace Directory Management
* **Story:** As a system, I want to shallow-clone the repository into a unique temporary directory and guarantee cleanup post-scan so that untrusted code cannot compromise the host environment.
* **SRS:** FR-04, NFR-01, NFR-04
* **Story Points:** 3
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-22, RSA-46
* **Acceptance Criteria:**
  - Clone uses `git clone --depth 1 --branch <branch> <url> <temp_dir>`.
  - Clones are bounded by a 60-second timeout and 100MB maximum size limit.
  - The temporary directory is deleted in a `finally` block regardless of scan success or failure.

#### US-09: Hardcoded Secret Detection
* **Story:** As a security analyst, I want the system to scan source code for exposed API keys, tokens, and private keys so that leaked credentials are identified immediately.
* **SRS:** FR-04
* **Story Points:** 5
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-17, O-07
* **Acceptance Criteria:**
  - Detects AWS access keys, GitHub personal access tokens, Stripe secret keys, and RSA/SSH private keys.
  - Identifies file path, start line, end line, and code snippet for each match.
  - Assigns severity `critical` or `high` with confidence `high`.

#### US-10: Source Code Vulnerability Analysis
* **Story:** As a security analyst, I want the system to analyze code for dangerous programming patterns (such as SQL injection and command injection) using Semgrep static analysis.
* **SRS:** FR-04
* **Story Points:** 3
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-18, O-08
* **Acceptance Criteria:**
  - Executes Semgrep subprocess with standardized security rulesets.
  - Captures vulnerability title, description, line numbers, and code context.

#### US-11: Dependency Vulnerability Checks
* **Story:** As a developer, I want the system to inspect `package.json` and `requirements.txt` against Google's Open Source Vulnerabilities (OSV) API so that vulnerable package versions are detected.
* **SRS:** FR-04
* **Story Points:** 3
* **Priority:** P0 (High)
* **Technical Tasks:** T-19, O-09
* **Acceptance Criteria:**
  - Queries `https://api.osv.dev/v1/query` for exact package names and pinned versions.
  - Extracts CVE identifiers, severity ratings, and remediation advisories.

#### US-12: Insecure Configuration Checks
* **Story:** As a security analyst, I want the system to detect committed `.env` files, enabled debug flags, and permissive CORS wildcards.
* **SRS:** FR-04
* **Story Points:** 2
* **Priority:** P0 (Medium)
* **Technical Tasks:** T-20
* **Acceptance Criteria:**
  - Flags committed environment secret files as `critical` severity.
  - Flags `DEBUG=True` and `allow_origins=["*"]` with appropriate recommendations.

#### US-32: Finding Normalizer Layer
* **Story:** As a system, I want to convert outputs from Gitleaks, Semgrep, OSV, and Config scanners into a unified `Finding` format so that the application maintains a consistent data contract.
* **SRS:** NFR-05, Data Requirements
* **Story Points:** 3
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-21
* **Acceptance Criteria:**
  - Transforms raw scanner dictionaries into SQLAlchemy `Finding` models.
  - Standardizes severity levels: `critical`, `high`, `medium`, `low`, `info`.
  - Standardizes confidence levels: `high`, `medium`, `low`.

#### US-13: Scan Progress Tracking & State Transitions
* **Story:** As a developer, I want to poll the status of my scan in real time so that I know when analysis is complete.
* **SRS:** FR-05, NFR-02
* **Story Points:** 3
* **Priority:** P0 (High)
* **Technical Tasks:** T-24, RSA-48
* **Acceptance Criteria:**
  - `GET /api/scans/{id}/status` returns current status and integer progress (0–100%).
  - Status follows deterministic machine: `queued` -> `running` -> `completed` / `failed` / `cancelled`.

#### US-14: In-Flight Scan Cancellation
* **Story:** As a developer, I want to cancel an active scan so that I can stop unwanted or stuck runs without saving partial findings.
* **SRS:** FR-05
* **Story Points:** 2
* **Priority:** P0 (High)
* **Technical Tasks:** T-24, RSA-48
* **Acceptance Criteria:**
  - `POST /api/scans/{id}/cancel` transitions queued or running scans to `cancelled`.
  - In-flight scanner execution is halted and partial findings are discarded.
  - Attempting to cancel an already completed or failed scan returns HTTP `422 Unprocessable Entity`.

---

### Epic 4: AI Explanations, Findings & PDF Reports

#### US-16: AI-Powered Finding Explanation & Remediation
* **Story:** As a developer, I want the LLM to explain the practical risk and provide exact code remediation for each detected vulnerability so that I understand how to fix it.
* **SRS:** FR-06, NFR-06
* **Story Points:** 5
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-25, T-26
* **Acceptance Criteria:**
  - Prompt sends concrete evidence (category, file, line, code snippet) to LLM.
  - LLM generates structured response: Practical Risk, Contextual Analysis, and Replacement Code.
  - Explanation is persisted in `findings.ai_explanation` column.

#### US-17: Findings Filtering & Workspace Inspection
* **Story:** As a developer, I want to view and filter all workspace findings by severity, confidence, category, and review status.
* **SRS:** FR-06
* **Story Points:** 3
* **Priority:** P0 (High)
* **Technical Tasks:** T-27, RSA-61
* **Acceptance Criteria:**
  - `GET /api/findings` supports multi-query filtering (`severity`, `confidence`, `reviewStatus`, `scanId`, `repositoryId`).
  - Results are paginated with total item and total page counts.

#### US-19: Finding Triage & Status Review
* **Story:** As a security analyst, I want to update the triage status of a finding (Open, Acknowledged, False Positive, Resolved) and attach review notes.
* **SRS:** FR-07
* **Story Points:** 2
* **Priority:** P0 (High)
* **Technical Tasks:** T-28
* **Acceptance Criteria:**
  - `PATCH /api/findings/{id}` updates `review_status` and `review_note`.
  - Sets `reviewed_by` to the current user ID and records `reviewed_at` timestamp.

#### US-21: AI Executive Summary & PDF Report Generation
* **Story:** As a developer, I want to generate a formal PDF security audit report summarizing the scan with an AI-generated executive summary.
* **SRS:** FR-08
* **Story Points:** 5
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-29, T-30, RSA-62
* **Acceptance Criteria:**
  - `POST /api/reports` initiates PDF assembly and transitions report status from `generating` to `ready`.
  - LLM generates a 2-paragraph Executive Summary evaluating overall repository risk posture.
  - Report includes cover page, executive summary, severity metrics table, and detailed finding breakdown.

#### US-22: PDF Preview & Binary Streaming
* **Story:** As a developer, I want to preview the security report in my browser or download it as a binary PDF file.
* **SRS:** FR-08
* **Story Points:** 2
* **Priority:** P0 (High)
* **Technical Tasks:** T-30, RSA-62
* **Acceptance Criteria:**
  - `GET /api/reports/{id}/pdf` returns `Content-Type: application/pdf`.
  - Browser preview returns `Content-Disposition: inline`.
  - Download requests (`?download=true`) return `Content-Disposition: attachment; filename="report-...pdf"`.

---

### Epic 5: Dashboard, History & Platform Delivery

#### US-24: Aggregated Dashboard Metrics
* **Story:** As a user, I want to view summary cards for total repositories, scan status breakdowns, finding severity counts, and recent activity.
* **SRS:** FR-09
* **Story Points:** 2
* **Priority:** P0 (High)
* **Technical Tasks:** T-31, RSA-71
* **Acceptance Criteria:**
  - `GET /api/dashboard/metrics` returns aggregated workspace metrics scoped to the authenticated user.

#### US-25: End-to-End Frontend Integration
* **Story:** As a team, we want the Next.js frontend connected end-to-end with the live FastAPI backend across all 5 user journeys.
* **SRS:** MVP Acceptance Criteria
* **Story Points:** 5
* **Priority:** P0 (Urgent)
* **Technical Tasks:** T-33 to T-40
* **Acceptance Criteria:**
  - Journey 1: User registers, signs in, and views live dashboard.
  - Journey 2: User adds real GitHub repo, validates existence, and lists branches.
  - Journey 3: User launches scan, monitors live progress, and observes completion.
  - Journey 4: User inspects findings, reads AI remediation, and updates review status.
  - Journey 5: User generates PDF report, previews in iframe, and downloads binary document.

---

## 4. Post-MVP Backlog Specification (Sprints 3 & 4 — P1 & P2 Priority)

| ID | User Story Title | SRS | Points | Target Sprint |
|---|---|:---:|:---:|:---:|
| **US-27** | GitHub OAuth 2.0 Account Linking | FR-01 | 5 | Sprint 3 |
| **US-30** | AST-Based Source Code Syntax Analysis | FR-04 | 8 | Sprint 3 |
| **US-31** | WebSocket Real-Time Scan Event Streaming | FR-05 | 5 | Sprint 3 |
| **US-32** | Cross-Scan LLM Finding Correlation & Deduplication | FR-06 | 5 | Sprint 3 |
| **US-33** | Multi-User Organization Workspaces & RBAC | FR-10 | 8 | Sprint 4 |