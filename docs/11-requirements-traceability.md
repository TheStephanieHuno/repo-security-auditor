# Requirements Traceability

## A. Forward Matrix

| Req ID | Summary | Source doc | UI screens/components that cover it (file:line) | UI coverage | Back-end work needed | Notes |
|---|---|---|---|---|---|---|
| PR-001 | Repository Registration | PRD | `src/app/repositories.tsx` (AddRepository form) | Full (Mocked) | Yes | Real API to persist repos |
| PR-002 | Repository Validation | PRD | `src/app/repositories.tsx:497` (Validate button) | Partial (Mocked) | Yes | Real GitHub API integration |
| PR-003 | Repository Information | PRD | `src/app/repositories.tsx` (RepositoryDetail) | Full (Mocked) | Yes | Fetch real repo metadata |
| PR-004 | Scan Initiation | PRD | `src/app/repositories.tsx` (scan page) | Full (Mocked) | Yes | Real scan orchestration |
| PR-005 | Scan Status | PRD | `src/app/scans.tsx` (ScanPage) | Full (Mocked) | Yes | Real-time polling/SSE |
| PR-006 | Security Analysis | PRD | N/A | Not applicable to UI | Yes | Implement 4 scanners |
| PR-007 | Finding Collection | PRD | N/A | Not applicable to UI | Yes | Worker result aggregation |
| PR-008 | Finding Normalization | PRD | N/A | Not applicable to UI | Yes | Normalizer component |
| PR-009 | Finding Evidence | PRD | `src/app/findings.tsx` (FindingDetail) | Full (Mocked) | Yes | Store/serve evidence |
| PR-010 | Finding Context | PRD | `src/app/findings.tsx` (FindingDetail) | Full (Mocked) | Yes | Context gathering logic |
| PR-011 | Finding Correlation | PRD | `src/app/findings.tsx` | Partial | Yes | Correlation logic |
| PR-012 | Finding Review | PRD | `src/app/findings.tsx` | Full (Mocked) | Yes | DB schema for review status |
| PR-013 | AI Explanation | PRD | `src/app/findings.tsx` | Partial (Mocked) | Yes | LLM Integration |
| PR-014 | Remediation Guidance | PRD | `src/app/findings.tsx` | Full (Mocked) | Yes | AI/Scanner recommendations |
| PR-015 | Uncertainty | PRD | `src/app/findings.tsx` | Partial | Yes | AI prompt engineering |
| PR-016 | Evidence Traceability | PRD | `src/app/findings.tsx` | Partial | Yes | DB associations |
| PR-017 | Dashboard | PRD | `src/app/dashboard.tsx` | Full (Mocked) | Yes | Aggregation API |
| PR-018 | Reporting | PRD | `src/app/reports.tsx` | Full (Mocked) | Yes | PDF generation API |
| PR-019 | Access Control | PRD | `src/app/store.tsx` | Partial (Mocked) | Yes | Authz middleware |
| PR-020 | Secure Analysis | PRD | N/A | Not applicable to UI | Yes | Worker isolation |
| FR-01 | Authentication | SRS | `src/app/auth.tsx` (Login) | Full (Mocked) | Yes | Real Auth provider |
| FR-02 | Repository Submission | SRS | `src/app/repositories.tsx` | Full (Mocked) | Yes | DB Insert |
| FR-03 | Repository Validation | SRS | `src/app/repositories.tsx` | Partial | Yes | Connectivity check |
| FR-04 | Security Scan | SRS | N/A | Not applicable to UI | Yes | Celery task execution |
| FR-05 | Scan Status | SRS | `src/app/scans.tsx` | Full (Mocked) | Yes | Real Redis/DB status |
| FR-06 | Findings | SRS | `src/app/findings.tsx` | Full (Mocked) | Yes | DB schema & API |
| FR-07 | Finding Review | SRS | `src/app/findings.tsx` | Full (Mocked) | Yes | Update endpoint |
| FR-08 | Security Report | SRS | `src/app/reports.tsx` | Full (Mocked) | Yes | Export API |
| FR-09 | Scan History | SRS | `src/app/scans.tsx` | Full (Mocked) | Yes | Scans list API |
| FR-10 | Access Control | SRS | `src/app/store.tsx` | Partial (Mocked) | Yes | Tenancy/Roles in DB |
| NFR-01 | Security | SRS | N/A | Not applicable to UI | Yes | Isolation strategy |
| NFR-02 | Performance | SRS | N/A | Not applicable to UI | Yes | Async task queue (Celery) |
| NFR-03 | Reliability | SRS | N/A | Not applicable to UI | Yes | Task retries/error handling |
| NFR-04 | Resource Limits | SRS | N/A | Not applicable to UI | Yes | Timeouts & quota config |
| NFR-05 | Extensibility | SRS | N/A | Not applicable to UI | Yes | Modular scanner design |
| NFR-06 | Usability | SRS | `src/app/findings.tsx` | Full | No | UI design satisfies this |
| MVP-AC-1 | Authenticate | SRS/PRD | `src/app/auth.tsx` | Full (Mocked) | Yes | Real Auth API |
| MVP-AC-2 | Submit GitHub repository | SRS/PRD | `src/app/repositories.tsx` | Full (Mocked) | Yes | Repo API |
| MVP-AC-3 | Start a security scan | SRS/PRD | `src/app/scans.tsx:90` | Full (Mocked) | Yes | Scan Trigger API |
| MVP-AC-4 | View scan progress/status | SRS/PRD | `src/app/scans.tsx` | Full (Mocked) | Yes | Status API |
| MVP-AC-5 | Detect security issues | SRS/PRD | N/A | Not applicable to UI | Yes | Core backend logic |
| MVP-AC-6 | View findings with evidence | SRS/PRD | `src/app/findings.tsx` | Full (Mocked) | Yes | Findings API |
| MVP-AC-7 | View security report | SRS/PRD | `src/app/reports.tsx` | Full (Mocked) | Yes | Reports API |
| MVP-AC-8 | Review previous scans | SRS/PRD | `src/app/scans.tsx` | Full (Mocked) | Yes | History API |
| MVP-AC-9 | Access only authorized info | SRS/PRD | `src/app/store.tsx` | Partial | Yes | RBAC/Tenancy |
| SEC-1 | Untrusted input | PRD | N/A | Not applicable to UI | Yes | Sandbox |
| SEC-2 | Isolated analysis | PRD | N/A | Not applicable to UI | Yes | Docker-in-Docker / VM |
| SEC-3 | Resource boundaries | PRD | N/A | Not applicable to UI | Yes | Cgroups / ulimits |
| SEC-4 | Restrict filesystem/network | PRD | N/A | Not applicable to UI | Yes | Egress filtering |
| SEC-5 | Credentials protected | PRD | N/A | Not applicable to UI | Yes | Vault / secrets manager |
| SEC-6 | Auth enforced | PRD | `src/app/shell.tsx` | Partial | Yes | API token validation |
| SEC-7 | Prompt injection risks | PRD | N/A | Not applicable to UI | Yes | Prompt engineering |
| SEC-8 | Sensitive info in logs/prompts | PRD | N/A | Not applicable to UI | Yes | Redaction logic |
| SEC-9 | Failures observable/handled safely | PRD | N/A | Not applicable to UI | Yes | Logging and alerts |

## B. Reverse Matrix

| UI element | Location (file:line) | Requirement(s) it satisfies | Status |
|---|---|---|---|
| Login Form | `src/app/auth.tsx:100` | FR-01, PR-019, MVP-AC-1 | Traced |
| Add Repository Form | `src/app/repositories.tsx:441` | PR-001, FR-02, MVP-AC-2 | Traced |
| Repository Validation | `src/app/repositories.tsx:497` | PR-002, FR-03 | Traced |
| Repository Detail View | `src/app/repositories.tsx` | PR-003 | Traced |
| Scan Trigger Button | `src/app/scans.tsx:90`, `repositories.tsx` | PR-004, MVP-AC-3 | Traced |
| Scan Status/Progress | `src/app/scans.tsx:280` | PR-005, FR-05, MVP-AC-4 | Traced |
| Scan History List | `src/app/scans.tsx` | FR-09, MVP-AC-8 | Traced |
| Findings List | `src/app/findings.tsx` | PR-012, FR-06 | Traced |
| Finding Detail / Evidence | `src/app/findings.tsx:363` | PR-009, MVP-AC-6, NFR-06 | Traced |
| Finding Review Status | `src/app/findings.tsx` | PR-012, FR-07 | Traced |
| Remediation / AI Guidance | `src/app/findings.tsx` | PR-014, PR-013 | Traced |
| Dashboard View | `src/app/dashboard.tsx` | PR-017 | Traced |
| Reports List | `src/app/reports.tsx` | PR-018, FR-08 | Traced |
| Export Report Button | `src/app/reports.tsx` | PR-018, MVP-AC-7 | Traced |
| Settings Form | `src/app/settings.tsx:182` | None | Orphan (Keep: Needed for user profile management) |
| Password Reset Form | `src/app/settings.tsx:615` | None | Orphan (Keep: Needed for standard auth flow) |
| Dark/Light Mode Toggle | `src/app/shell.tsx:341` | None | Orphan (Keep: standard UX) |

**Recommendations for Orphans:**
- **Settings Form (Profile):** Keep. Add requirement for User Management.
- **Password Reset:** Keep. Add requirement for Auth Recovery.
- **Theme Toggle:** Keep. General UX improvement.
