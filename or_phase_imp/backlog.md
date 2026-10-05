

\## SRS Traceability Matrix



| SRS Ref | Requirement | User Stories |

|---------|-------------|--------------|

| FR-01 | Authentication | US-01, US-02, US-03 |

| FR-02 | Repository Submission | US-04 |

| FR-03 | Repository Validation | US-05 |

| FR-04 | Security Scan | US-06, US-07, US-08, US-09, US-10 |

| FR-05 | Scan Status | US-11, US-12 |

| FR-06 | Findings | US-13, US-14 |

| FR-07 | Finding Review | US-15 |

| FR-08 | Security Report | US-16, US-17 |

| FR-09 | Scan History | US-18 |

| FR-10 | Access Control | US-19 |

| NFR-01 | Isolated Scanning | US-20 |

| NFR-02 | Async Scanning | US-21 |

| NFR-03 | Check Resilience | US-22 |

| NFR-04 | Resource Limits | US-23 |

| NFR-05 | Extensibility | US-24 |

| NFR-06 | Usability (AI Explanations) | US-25 |



\---



\## Priority Definitions



\- \*\*P0:\*\* Must have for MVP release probably this week.

\- \*\*P1:\*\* Should have if time permits within the sprint.

\- \*\*P2:\*\* Scheduled for post-MVP sprints.



\## Status Definitions



\- \*\*Done:\*\* Implemented, tested, and verified.

\- \*\*In Progress:\*\* Actively being developed.

\- \*\*To Do:\*\* Not yet started.

\- \*\*Blocked:\*\* Cannot proceed due to external dependency.



\---



\## P0 — MVP (Sprint 2, Current Week)



| ID | User Story | SRS | Type | Points | Status |

|----|-----------|-----|------|--------|--------|

| US-01 | As a user, I want to register and sign in with JWT authentication. | FR-01 | Core | 2 | To Do |

| US-02 | As a system, I want to store user roles (developer, analyst, administrator). | FR-01 | Core | 1 | To Do |

| US-03 | As a user, I want to sign out and have my token invalidated. | FR-01 | Core | 1 | To Do |

| US-04 | As a developer, I want to submit a GitHub repository URL for scanning. | FR-02 | Core | 2 | To Do |

| US-05 | As a system, I want to validate the repository exists via the real GitHub API. | FR-03 | Core | 3 | To Do |

| US-06 | As a system, I want to clone the repository into an isolated temporary directory. | FR-04, NFR-01 | Core | 3 | To Do |

| US-07 | As a system, I want to detect exposed secrets using regex pattern matching. | FR-04 | Core | 5 | To Do |

| US-08 | As a system, I want to check dependencies against known vulnerability patterns. | FR-04 | Core | 3 | To Do |

| US-09 | As a system, I want to check for insecure configurations. | FR-04 | Core | 2 | To Do |

| US-10 | As a user, I want the LLM to explain each finding with risk and remediation. | FR-06, NFR-06 | AI | 5 | To Do |

| US-11 | As a user, I want to poll scan progress asynchronously. | FR-05, NFR-02 | Core | 3 | To Do |

| US-12 | As a user, I want to cancel a queued or running scan. | FR-05 | Core | 2 | To Do |

| US-13 | As a user, I want to view findings with severity, confidence, evidence, and AI explanation. | FR-06 | Core/AI | 3 | To Do |

| US-14 | As a user, I want to filter findings by severity, confidence, and category. | FR-06 | Core | 2 | To Do |

| US-15 | As a security analyst, I want to review a finding by setting status and adding a note. | FR-07 | Core | 2 | To Do |

| US-16 | As a user, I want to generate a PDF report with an AI-written executive summary. | FR-08 | AI | 5 | To Do |

| US-17 | As a user, I want to preview and download the PDF report. | FR-08 | Core | 2 | To Do |

| US-18 | As a user, I want to view scan history for my repositories. | FR-09 | Core | 2 | To Do |

| US-19 | As a system, I want to enforce that users only access their own resources. | FR-10 | Core | 3 | To Do |

| US-20 | As a system, I want to use isolated temp directories with automatic cleanup. | NFR-01 | Core | 2 | To Do |

| US-21 | As a system, I want scans to run as background tasks. | NFR-02 | Core | 2 | To Do |

| US-22 | As a system, I want a failure in one check to not discard results from other checks. | NFR-03 | Core | 2 | To Do |

| US-23 | As a system, I want to enforce a 5-minute timeout and 100MB clone limit per scan. | NFR-04 | Core | 2 | To Do |

| US-24 | As a developer, I want a pluggable scanner architecture for extensibility. | NFR-05 | Core | 3 | To Do |

| US-25 | As a team, we want the frontend connected end-to-end to the live backend. | All | Core | 5 | To Do |



\*\*MVP Total: 65 story points\*\*



\---



\## P2 — Post-MVP (Sprint 3 and Beyond)



| ID | User Story | SRS | Points | Status |

|----|-----------|-----|--------|--------|

| US-26 | GitHub OAuth login flow | FR-01 | 5 | To Do |

| US-27 | Real SMTP password reset emails | FR-01 | 3 | To Do |

| US-28 | AST-based code analysis for Python and JavaScript | FR-04 | 8 | To Do |

| US-29 | WebSocket real-time scan progress streaming | FR-05 | 5 | To Do |

| US-30 | LLM cross-scan finding correlation | FR-06 | 5 | To Do |

| US-31 | Multi-user workspace with role-based access control | FR-10 | 8 | To Do |

| US-32 | False positive marking with audit trail | FR-07 | 3 | To Do |

| US-33 | LLM-generated remediation pull requests | FR-06 | 8 | To Do |

