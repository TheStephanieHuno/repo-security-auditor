# Open Questions

## Product & Scope
1. **AI Features:** The PRD mandates AI explanation, context gathering, and correlation, but the SRS explicitly defines the MVP scope without them. Should the AI functionality be built for MVP, or deferred? 
   - *Blocks:* Backend AI integration phase; `findings.tsx` AI UI implementation.
2. **Scan Status Granularity:** The UI implements 10 granular scan stages, but the SRS defines only 4 states (queued, running, completed, failed). Can the backend emit 10 stages, or must the UI be simplified?
   - *Blocks:* Scan worker status update logic; UI progress bar accuracy.
3. **Finding Review Persistence:** The UI allows users to mark findings as "False positive" or "Resolved". Should these states persist automatically when the repository is scanned again?
   - *Blocks:* Finding normalization and de-duplication backend logic.

## Security & Architecture
4. **Dependency Scanner Tool:** The Architecture Guide references OSV for dependency scanning, but the Stack document and UI reference Trivy. Which tool is authoritative?
   - *Blocks:* Celery task implementation for dependency scanning.
5. **Sandbox Infrastructure:** Security constraints mandate analyzing untrusted repositories in an isolated environment. What infrastructure mechanism will provide this boundary (e.g., Docker-in-Docker, Kata Containers, gVisor, or ephemeral VMs)?
   - *Blocks:* DevOps / Infrastructure provisioning; Celery worker configuration.

## Identity & Access Management
6. **Admin / User Management:** The SRS requires an "Administrator" role to manage users, but the UI has no screens for user provisioning, inviting teammates, or role management. How are users onboarded?
   - *Blocks:* Backend users router; Admin dashboard UI creation.
7. **GitHub Credentials:** Private repository access requires PATs (Personal Access Tokens) or a GitHub App integration. The UI mock implies immediate connection, and the DB schema lacks a secure credential store. How will tokens be gathered and vaulted securely?
   - *Blocks:* Repository Registration flow; Backend vault architecture.
