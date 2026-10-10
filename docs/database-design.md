\# Database Design Specification (DDS)



\*\*Project:\*\* Repo Security Auditor  

\*\*Document Version:\*\* 1.0  

\*\*Date:\*\* October 8, 2026  

\*\*Target Systems:\*\* PostgreSQL 16 (Production) / SQLite 3 (Development)  

\*\*ORM Framework:\*\* SQLAlchemy 2.0 (Async Engine)  

\*\*SRS Reference:\*\* Section 6 (Data Requirements), FR-01, FR-02, FR-04, FR-06, FR-08, FR-10  



\---



\## 1. Overview \& Objectives



This specification defines the logical and physical data architecture for \*\*Repo Security Auditor\*\*. The database is designed to support high-throughput, asynchronous repository security scans, multi-scanner result aggregation, finding triage workflows, and AI-assisted PDF report generation while enforcing strict tenant isolation at the relational level.



\### Core Data Design Goals:

\- \*\*Strict Referential Integrity:\*\* Enforce foreign key constraints with explicit cascading delete rules to eliminate orphaned scan artifacts.

\- \*\*Third Normal Form (3NF) Compliance:\*\* Eliminate data redundancy and update anomalies across repository, scan, and vulnerability entities.

\- \*\*Tenant Data Isolation:\*\* Ensure all data records link deterministically back to a user ownership boundary to support Insecure Direct Object Reference (IDOR) prevention.

\- \*\*Audit Traceability:\*\* Provide deterministic timestamps (`created\_at`, `updated\_at`, `reviewed\_at`) across all state-mutating tables.



\---



\## 2. Conceptual Schema \& Business Rules



```

┌─────────────┐       1 : N       ┌──────────────────┐       1 : N       ┌─────────────┐

│    USERS    │ ────────────────► │   REPOSITORIES   │ ────────────────► │    SCANS    │

└─────────────┘                   └──────────────────┘                   └──────┬──────┘

&#x20;                                                                               │

&#x20;                                                                ┌──────────────┴──────────────┐

&#x20;                                                          1 : N │                       1 : N │

&#x20;                                                                ▼                             ▼

&#x20;                                                         ┌─────────────┐               ┌─────────────┐

&#x20;                                                         │  FINDINGS   │               │   REPORTS   │

&#x20;                                                         └─────────────┘               └─────────────┘

```



\### Cardinality \& Business Rules:

1\. \*\*User to Repository (`1:N`):\*\* A registered user may submit zero or more repositories. Each repository belongs exclusively to one user (`added\_by`).

2\. \*\*Repository to Scan (`1:N`):\*\* A repository may undergo zero or more scans across varying branches and commit points. Each scan belongs to exactly one repository.

3\. \*\*Scan to Finding (`1:N`):\*\* A scan execution produces zero or more normalized findings. Each finding is permanently bound to the scan that identified it.

4\. \*\*Scan to Report (`1:N`):\*\* A completed scan can generate zero or more compiled report documents (PDF generation attempts). Each report belongs to exactly one scan.

5\. \*\*Cascading Lifecycle:\*\*

&#x20;  - Deletion of a `User` cascades to all associated `Repositories`, `Scans`, `Findings`, and `Reports`.

&#x20;  - Deletion of a `Repository` cascades to all associated `Scans`, `Findings`, and `Reports`.

&#x20;  - Deletion of a `Scan` cascades to all child `Findings` and `Reports`.



\---



\## 3. Entity-Relationship Diagram (ERD)



```mermaid

erDiagram

&#x20;   USERS ||--o{ REPOSITORIES : "registers / owns"

&#x20;   USERS ||--o{ SCANS : "initiates"

&#x20;   REPOSITORIES ||--o{ SCANS : "undergoes"

&#x20;   REPOSITORIES ||--o{ FINDINGS : "contains"

&#x20;   SCANS ||--o{ FINDINGS : "identifies"

&#x20;   SCANS ||--o{ REPORTS : "compiled\_into"



&#x20;   USERS {

&#x20;       UUID id PK "Unique User Identifier"

&#x20;       VARCHAR\_255 name "Full Display Name"

&#x20;       VARCHAR\_255 email UK "Unique Login Email"

&#x20;       VARCHAR\_255 hashed\_password "Bcrypt Hash (Cost Factor 12)"

&#x20;       VARCHAR\_50 role "developer | security\_analyst | administrator"

&#x20;       BOOLEAN on\_scan\_completion "Notification Preference"

&#x20;       BOOLEAN on\_scan\_failure "Notification Preference"

&#x20;       BOOLEAN is\_verified "Email Verification Flag"

&#x20;       TIMESTAMPTZ created\_at "Account Creation Timestamp"

&#x20;       TIMESTAMPTZ updated\_at "Account Last Update Timestamp"

&#x20;   }



&#x20;   REPOSITORIES {

&#x20;       UUID id PK "Unique Repository Identifier"

&#x20;       VARCHAR\_1024 url "Target GitHub Repository URL"

&#x20;       VARCHAR\_255 name "Repository Name"

&#x20;       VARCHAR\_255 owner "Repository Owner / Org Name"

&#x20;       VARCHAR\_50 provider "github"

&#x20;       VARCHAR\_255 default\_branch "Default Git Branch (main/master)"

&#x20;       BOOLEAN is\_valid "Pre-flight Verification State"

&#x20;       UUID added\_by FK "References USERS(id) ON DELETE CASCADE"

&#x20;       TIMESTAMPTZ created\_at "Registration Timestamp"

&#x20;       TIMESTAMPTZ updated\_at "Last Update Timestamp"

&#x20;   }



&#x20;   SCANS {

&#x20;       UUID id PK "Unique Scan Identifier"

&#x20;       UUID repository\_id FK "References REPOSITORIES(id) ON DELETE CASCADE"

&#x20;       UUID initiated\_by FK "References USERS(id)"

&#x20;       VARCHAR\_255 branch "Target Branch Analyzed"

&#x20;       VARCHAR\_50 status "queued | running | completed | failed | cancelled"

&#x20;       INTEGER progress "Execution Progress (0 - 100)"

&#x20;       TIMESTAMPTZ started\_at "Worker Execution Start Timestamp"

&#x20;       TIMESTAMPTZ completed\_at "Terminal State Timestamp"

&#x20;       TIMESTAMPTZ cancelled\_at "Cancellation Timestamp"

&#x20;       TIMESTAMPTZ created\_at "Job Creation Timestamp"

&#x20;       TIMESTAMPTZ updated\_at "Record Last Update Timestamp"

&#x20;   }



&#x20;   FINDINGS {

&#x20;       UUID id PK "Unique Finding Identifier"

&#x20;       UUID scan\_id FK "References SCANS(id) ON DELETE CASCADE"

&#x20;       UUID repository\_id FK "References REPOSITORIES(id) ON DELETE CASCADE"

&#x20;       VARCHAR\_50 severity "critical | high | medium | low | info"

&#x20;       VARCHAR\_50 confidence "high | medium | low"

&#x20;       VARCHAR\_255 category "Secret | Code | Dependency | Config"

&#x20;       VARCHAR\_500 title "Vulnerability Headline"

&#x20;       TEXT description "Detailed Issue Narrative"

&#x20;       VARCHAR\_1024 file\_path "Relative Repository Path"

&#x20;       INTEGER line\_start "Source Code Start Line"

&#x20;       INTEGER line\_end "Source Code End Line"

&#x20;       TEXT code\_snippet "Evidence Excerpt"

&#x20;       TEXT recommendation "Remediation Instructions"

&#x20;       TEXT ai\_explanation "LLM Contextual Explanation \& Guidance"

&#x20;       VARCHAR\_50 review\_status "open | acknowledged | false\_positive | resolved"

&#x20;       TEXT review\_note "Security Analyst Triage Notes"

&#x20;       UUID reviewed\_by FK "References USERS(id)"

&#x20;       TIMESTAMPTZ reviewed\_at "Triage Action Timestamp"

&#x20;       TIMESTAMPTZ created\_at "Finding Detection Timestamp"

&#x20;   }



&#x20;   REPORTS {

&#x20;       UUID id PK "Unique Report Identifier"

&#x20;       UUID scan\_id FK "References SCANS(id) ON DELETE CASCADE"

&#x20;       VARCHAR\_50 status "generating | ready | failed"

&#x20;       VARCHAR\_10 format "pdf"

&#x20;       VARCHAR\_1024 file\_url "Local Path / Object Storage Key"

&#x20;       INTEGER file\_size "Report Size in Bytes"

&#x20;       TIMESTAMPTZ created\_at "Generation Request Timestamp"

&#x20;       TIMESTAMPTZ completed\_at "Assembly Completion Timestamp"

&#x20;   }

```



\---



\## 4. Data Dictionary (Table Specifications)



\### 4.1 Table: `users`

Maintains user identity, cryptographic authentication credentials, authorization roles, and notification preferences.



| Column | Data Type | Nullable | Default | Constraints | Description |

|---|---|:---:|---|---|---|

| `id` | `UUID` | No | `uuid\_generate\_v4()` | `PRIMARY KEY` | Globally unique identifier for the user account. |

| `name` | `VARCHAR(255)` | No | — | — | Full display name of the user. |

| `email` | `VARCHAR(255)` | No | — | `UNIQUE`, `INDEX` | User login email address; must be normalized to lowercase. |

| `hashed\_password` | `VARCHAR(255)` | No | — | — | Bcrypt hash string with cost factor 12. |

| `role` | `VARCHAR(50)` | No | `'developer'` | `CHECK(role IN ('developer', 'security\_analyst', 'administrator'))` | Authorization role defining feature access boundaries. |

| `on\_scan\_completion` | `BOOLEAN` | No | `TRUE` | — | User toggle for scan completion notifications. |

| `on\_scan\_failure` | `BOOLEAN` | No | `TRUE` | — | User toggle for scan failure notifications. |

| `is\_verified` | `BOOLEAN` | No | `FALSE` | — | Indicates whether the email has completed verification. |

| `created\_at` | `TIMESTAMPTZ` | No | `NOW()` | — | UTC timestamp of account creation. |

| `updated\_at` | `TIMESTAMPTZ` | No | `NOW()` | — | UTC timestamp of the most recent profile mutation. |



\---



\### 4.2 Table: `repositories`

Maintains tracked GitHub repositories associated with user workspaces.



| Column | Data Type | Nullable | Default | Constraints | Description |

|---|---|:---:|---|---|---|

| `id` | `UUID` | No | `uuid\_generate\_v4()` | `PRIMARY KEY` | Globally unique identifier for the repository. |

| `url` | `VARCHAR(1024)` | No | — | — | Fully qualified GitHub URL (e.g., `https://github.com/org/repo`). |

| `name` | `VARCHAR(255)` | No | — | — | Derived repository display name. |

| `owner` | `VARCHAR(255)` | No | — | — | GitHub organization or individual account name. |

| `provider` | `VARCHAR(50)` | No | `'github'` | — | Source code host provider identifier. |

| `default\_branch` | `VARCHAR(255)` | No | `'main'` | — | Identified primary branch (e.g., `main`, `master`). |

| `is\_valid` | `BOOLEAN` | No | `TRUE` | — | Verification status verified against live GitHub API. |

| `added\_by` | `UUID` | No | — | `FOREIGN KEY` $\\rightarrow$ `users(id)` `ON DELETE CASCADE`, `INDEX` | Owning user account identifier (enforces FR-10). |

| `created\_at` | `TIMESTAMPTZ` | No | `NOW()` | — | UTC timestamp when repository was registered. |

| `updated\_at` | `TIMESTAMPTZ` | No | `NOW()` | — | UTC timestamp of last metadata synchronization. |



\---



\### 4.3 Table: `scans`

Tracks the lifecycle, execution progress, and execution metadata for every security analysis job.



| Column | Data Type | Nullable | Default | Constraints | Description |

|---|---|:---:|---|---|---|

| `id` | `UUID` | No | `uuid\_generate\_v4()` | `PRIMARY KEY` | Globally unique identifier for the scan job. |

| `repository\_id` | `UUID` | No | — | `FOREIGN KEY` $\\rightarrow$ `repositories(id)` `ON DELETE CASCADE`, `INDEX` | Target repository under evaluation. |

| `initiated\_by` | `UUID` | No | — | `FOREIGN KEY` $\\rightarrow$ `users(id)` | User who dispatched the scan execution. |

| `branch` | `VARCHAR(255)` | No | — | — | Target Git branch checked out in the temporary workspace. |

| `status` | `VARCHAR(50)` | No | `'queued'` | `CHECK(status IN ('queued', 'running', 'completed', 'failed', 'cancelled'))`, `INDEX` | Deterministic state machine status. |

| `progress` | `INTEGER` | No | `0` | `CHECK(progress >= 0 AND progress <= 100)` | Real-time percentage progress of background execution. |

| `started\_at` | `TIMESTAMPTZ` | Yes | `NULL` | — | UTC timestamp when the background worker began cloning. |

| `completed\_at` | `TIMESTAMPTZ` | Yes | `NULL` | — | UTC timestamp when scan reached `completed` or `failed`. |

| `cancelled\_at` | `TIMESTAMPTZ` | Yes | `NULL` | — | UTC timestamp when user initiated cancellation. |

| `created\_at` | `TIMESTAMPTZ` | No | `NOW()` | — | UTC timestamp when the job was enqueued. |

| `updated\_at` | `TIMESTAMPTZ` | No | `NOW()` | — | UTC timestamp of last status or progress change. |



\---



\### 4.4 Table: `findings`

Stores standardized vulnerability records aggregated from Gitleaks, Semgrep, OSV API, and Configuration checks.



| Column | Data Type | Nullable | Default | Constraints | Description |

|---|---|:---:|---|---|---|

| `id` | `UUID` | No | `uuid\_generate\_v4()` | `PRIMARY KEY` | Globally unique identifier for the finding. |

| `scan\_id` | `UUID` | No | — | `FOREIGN KEY` $\\rightarrow$ `scans(id)` `ON DELETE CASCADE`, `INDEX` | Scan execution instance that detected the vulnerability. |

| `repository\_id` | `UUID` | No | — | `FOREIGN KEY` $\\rightarrow$ `repositories(id)` `ON DELETE CASCADE`, `INDEX` | Repository where vulnerability is located. |

| `severity` | `VARCHAR(50)` | No | — | `CHECK(severity IN ('critical', 'high', 'medium', 'low', 'info'))`, `INDEX` | Severity rating assigned by scanner and normalizer. |

| `confidence` | `VARCHAR(50)` | No | `'high'` | `CHECK(confidence IN ('high', 'medium', 'low'))`, `INDEX` | Detection confidence level (SRS FR-06). |

| `category` | `VARCHAR(255)` | No | — | `INDEX` | Taxonomy category: `Secret Exposure`, `Source Code Vulnerability`, `Dependency Vulnerability`, `Insecure Configuration`. |

| `title` | `VARCHAR(500)` | No | — | — | Short issue summary headline. |

| `description` | `TEXT` | No | — | — | Full vulnerability explanation and context. |

| `file\_path` | `VARCHAR(1024)` | No | — | — | Relative file path within the repository root. |

| `line\_start` | `INTEGER` | Yes | `NULL` | — | Starting line number of the offending code snippet. |

| `line\_end` | `INTEGER` | Yes | `NULL` | — | Ending line number of the offending code snippet. |

| `code\_snippet` | `TEXT` | Yes | `NULL` | — | Concrete evidence code excerpt extracted during analysis. |

| `recommendation` | `TEXT` | No | — | — | Standard technical remediation guidance. |

| `ai\_explanation` | `TEXT` | Yes | `NULL` | — | LLM-generated risk evaluation and replacement code. |

| `review\_status` | `VARCHAR(50)` | No | `'open'` | `CHECK(review\_status IN ('open', 'acknowledged', 'false\_positive', 'resolved'))`, `INDEX` | Current analyst triage state. |

| `review\_note` | `TEXT` | Yes | `NULL` | — | Analyst-authored explanation during review triage. |

| `reviewed\_by` | `UUID` | Yes | `NULL` | `FOREIGN KEY` $\\rightarrow$ `users(id)` | Security analyst who updated the triage status. |

| `reviewed\_at` | `TIMESTAMPTZ` | Yes | `NULL` | — | UTC timestamp when triage review was saved. |

| `created\_at` | `TIMESTAMPTZ` | No | `NOW()` | — | UTC timestamp when finding was normalized and stored. |



\---



\### 4.5 Table: `reports`

Maintains compilation status, metadata, and binary file pointers for generated PDF security audits.



| Column | Data Type | Nullable | Default | Constraints | Description |

|---|---|:---:|---|---|---|

| `id` | `UUID` | No | `uuid\_generate\_v4()` | `PRIMARY KEY` | Globally unique identifier for the report document. |

| `scan\_id` | `UUID` | No | — | `FOREIGN KEY` $\\rightarrow$ `scans(id)` `ON DELETE CASCADE`, `INDEX` | Scan summarized within this PDF document. |

| `status` | `VARCHAR(50)` | No | `'generating'` | `CHECK(status IN ('generating', 'ready', 'failed'))` | PDF rendering state lifecycle. |

| `format` | `VARCHAR(10)` | No | `'pdf'` | — | Target document format. |

| `file\_url` | `VARCHAR(1024)` | Yes | `NULL` | — | Local filesystem path or object storage key for binary streaming. |

| `file\_size` | `INTEGER` | Yes | `NULL` | — | Compiled binary PDF size in bytes. |

| `created\_at` | `TIMESTAMPTZ` | No | `NOW()` | — | UTC timestamp when report was requested. |

| `completed\_at` | `TIMESTAMPTZ` | Yes | `NULL` | — | UTC timestamp when PDF compilation finished. |



\---



\## 5. Normalization Analysis (Proof of 3NF)



The schema complies with \*\*Third Normal Form (3NF)\*\* standards across all tables:



\### 5.1 First Normal Form (1NF) Compliance:

\- \*\*Atomicity:\*\* All attributes contain scalar, non-decomposable values. No composite arrays, lists, or unparsed multi-value strings are stored in single fields.

\- \*\*Primary Keys:\*\* Every relation defines an unambiguous single-column primary key (`id` of type `UUID`).



\### 5.2 Second Normal Form (2NF) Compliance:

\- \*\*No Partial Key Dependencies:\*\* All tables utilize single-attribute primary keys (`id`). Therefore, no non-prime attribute can depend on a proper subset of any candidate key.



\### 5.3 Third Normal Form (3NF) Compliance:

\- \*\*No Transitive Dependencies:\*\* Every non-prime attribute depends solely on the primary key:

&#x20; - In `findings`, attributes such as `file\_path`, `line\_start`, and `severity` describe the vulnerability itself, not the parent `Scan` or `Repository`.

&#x20; - In `repositories`, metadata attributes (`name`, `default\_branch`) describe the codebase, not the user who registered it.

&#x20; - In `scans`, operational metrics (`status`, `progress`, `started\_at`) depend solely on the `scan\_id`.

\- There are no transitive functional dependencies of the form $X \\rightarrow Y$ and $Y \\rightarrow Z$ where $Z$ is a non-prime attribute.



\---



\## 6. Indexing \& Query Optimization Strategy



The indexing strategy targets high-frequency query paths defined in the REST API specification:



```sql

\-- 1. Multi-Tenant User Isolation \& Ownership Traversal (FR-10)

CREATE INDEX idx\_repositories\_added\_by ON repositories(added\_by);

CREATE INDEX idx\_scans\_repository\_id ON scans(repository\_id);

CREATE INDEX idx\_findings\_scan\_id ON findings(scan\_id);

CREATE INDEX idx\_findings\_repository\_id ON findings(repository\_id);

CREATE INDEX idx\_reports\_scan\_id ON reports(scan\_id);



\-- 2. Workspace Findings Filtering Optimization (GET /api/findings)

CREATE INDEX idx\_findings\_severity ON findings(severity);

CREATE INDEX idx\_findings\_confidence ON findings(confidence);

CREATE INDEX idx\_findings\_review\_status ON findings(review\_status);

CREATE INDEX idx\_findings\_category ON findings(category);

CREATE INDEX idx\_findings\_created\_at ON findings(created\_at DESC);



\-- 3. Scan Lifecycle Polling \& Status Filtering (GET /api/scans/{id}/status)

CREATE INDEX idx\_scans\_status ON scans(status);

CREATE INDEX idx\_scans\_created\_at ON scans(created\_at DESC);



\-- 4. User Authentication Lookup

CREATE UNIQUE INDEX idx\_users\_email ON users(LOWER(email));

```



\---



\## 7. Security, Access Control \& Data Isolation (SRS FR-10)



The relational schema implements tenant boundaries using \*\*foreign key ownership hierarchies\*\*:



```

User (Tenant Root)

&#x20; └── Repository (WHERE added\_by = user.id)

&#x20;       └── Scan (WHERE repository.added\_by = user.id)

&#x20;             ├── Finding (WHERE repository.added\_by = user.id)

&#x20;             └── Report (WHERE repository.added\_by = user.id)

```



Every single-resource endpoint (`/repositories/{id}`, `/scans/{id}`, `/findings/{id}`, `/reports/{id}`) executes an inner join back to `repositories.added\_by`. If the foreign key relationship does not match `current\_user.id`, the query returns null, resolving to an HTTP `404 Not Found`. This prevents Insecure Direct Object Reference (IDOR / OWASP A01) vulnerabilities at the data access layer.

