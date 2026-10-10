# Project change report

## 1. Summary

Repo Security Auditor has moved from a clickable sample interface toward a server-ready product front end.
All business information now has one central route to the future server, while sample data remains available for demonstrations.
Visitors must sign in or create an account before using the protected workspace.
Users can add repositories, choose branches, start or cancel scans, review findings, and create PDF reports.
Password recovery, GitHub connection, profile settings, and notification preferences now have defined server requests.
Fake administration and demonstration controls were removed from normal screens or hidden for development use.
Development navigation was improved without changing the already-fast production build.
The checks in section 8 pass except that lint reports warnings only.

## 2. What changed
q
### Product foundation

| Before | Now | Why it matters |
|---|---|---|
| Screens read and changed information in several local places. | One central data service is used for repositories, scans, findings, reports, accounts, settings, and GitHub. Each future server request has a ready place to be connected. | The real server can be added feature by feature without rewriting every screen. |
| The old local data store held business information. | That old store was deleted. Only visual preferences such as theme and sidebar state remain local. | Business information has one clear owner. |
| The product was mainly a visual sample. | Sample mode is switchable from the same central service as future live mode. | Reviewers can use the product now while the server is built later. |

### Login and account access

| Before | Now | Why it matters |
|---|---|---|
| Login was a sample form and wrong credentials could lead to an unstable page. | Login and sign-up are the first pages for logged-out visitors. Wrong credentials show an inline error. Logged-in visitors are sent to the workspace instead of seeing login again. | The entry experience is predictable and safe. |
| Password recovery only displayed a preview message. | Users can request instructions and use a public set-new-password screen with a token. | The front end now matches a real recovery journey. |

### Repositories and scanning

| Before | Now | Why it matters |
|---|---|---|
| Scans were shown as a simulated process with limited branch choice. | Users choose a branch from the repository before starting a scan. | Teams can check the branch they actually intend to release or review. |
| Users saw several inconsistent scan action names. | Starting uses “Start security scan”; a new run after a result uses “Rescan”. | The same action is easier to recognize across the workspace. |
| Users could see a disabled cancel control. | Queued or running scans can be cancelled after confirmation. | Users can stop an unwanted or stuck run. |
| Status could be treated as screen-owned state. | Scan status is reported by the system and cannot be edited by users. | Results have a trustworthy source. |
| Failed runs had retry wording and cancelled runs were not represented. | Failed and cancelled runs can be rescanned, with the previous branch selected first and still changeable. | Recovery is clear and preserves the user’s context. |

### Findings and reports

| Before | Now | Why it matters |
|---|---|---|
| Reports were described as markdown or a local demo action. | Reports are PDF documents with system-reported generating, ready, or failed states. | The output matches the intended handoff format. |
| There was no report preview. | Ready reports can be previewed in the browser and downloaded. | A user can inspect the document before saving it. |
| A failed report used a demo completion button. | A failed report can be generated again through the normal report action. | Recovery follows the real report process. |
| Guidance and evidence were presented as separate sample areas. | Findings include severity, confidence, evidence, ownership status, and remediation guidance. | Reviewers can distinguish scanner evidence from explanation and action. |

The back end will have the AI write the report content and produce the PDF on the server.

### Settings and visual quality

| Before | Now | Why it matters |
|---|---|---|
| Settings showed sample users, role changes, repository access previews, and an internal state explorer. | Those features were removed from normal settings. Reset sample data is available only when development tools are explicitly enabled. | Internal demonstrations are not mistaken for real administration. |
| GitHub and notifications were local-only examples. | GitHub connection and notification preferences have defined server requests and clear success/error messages. | These features have a direct path to production services. |
| Screens used different loading, empty, error, and recovery wording. | Shared screen patterns and recovery actions are used across the main flows. | Users receive more consistent guidance. |

### Development performance and documentation

| Before | Now | Why it matters |
|---|---|---|
| Development navigation was slowed by a special development bundling setting. | That override was removed, the development server uses Turbopack, and Lucide imports are optimized. | Route changes are simpler to build during development. |
| Production was already fast. | The production settings were preserved; only development configuration changed. | The improvement work did not trade away production performance. |
| Product behavior and screens were spread across informal notes. | The `docs/user-flows/` set records journeys, links/actions, requirements, conflicts, data decisions, backend responsibilities, open questions, and review decisions. | Product, design, and backend teams have a shared reference. |

The available git history shows the original project files, the documentation-folder move, and the UI scaffold. Feature-by-feature history for later work is not visible in git history.

## 3. Removed items

- The old business-data store and its provider.
- Markdown report export and the fake “Complete demo generation” control.
- The Settings Users tab and sample role selector.
- The repository-access preview and internal state explorer.
- Normal-screen demo login, reset, and sample-data controls unless development tools are enabled.
- The fake forgot-password preview.
- Disabled cancellation wording and inconsistent scan retry wording.
- Direct browser storage for business information outside the sample-data service.

## 4. New screens and controls

- Sign-up for new accounts.
- Public `/reset-password?token=...` screen for setting a new password.
- Branch selection when starting or rescanning a repository.
- Cancel-scan confirmation: “Cancel this scan? Results found so far will not be saved.”
- Rescan actions for failed, cancelled, and completed scans.
- Report generation status, PDF preview, download, and generate-again action.
- GitHub connect/disconnect and notification preference controls connected to defined server requests.
- Consistent loading, empty, error, and recovery actions across the workspace.

## 5. What the back-end team must build

The table below is the complete list in `docs/18-api-integration-guide.md`. “Sends” describes the information the screen provides; “returns” describes what the screen needs back.

| Screen or feature | What it does in plain words | Method and server address | Sends | Returns |
|---|---|---|---|---|
| Sign in | Signs an existing user in | POST `/api/auth/login` | Email and password | Sign-in token |
| Sign up | Creates a user account | POST `/api/auth/register` | Name, email, password | Sign-in token |
| Sign out | Ends the current session | POST `/api/auth/logout` | Nothing | Empty success |
| Current user | Checks who is signed in | GET `/api/users/me` | Nothing | User and session details |
| Request password reset | Sends reset instructions without revealing account existence | POST `/api/auth/password-reset/request` | Email | Neutral success |
| Set new password | Changes a password using a reset link | POST `/api/auth/password-reset/confirm` | Reset token and new password | Success or invalid/expired error |
| Update profile | Saves name and email | PUT `/api/users/me` | Name and email | Updated user |
| Change password | Changes the password from Settings | PUT `/api/users/me/password` | Current and new password | Empty success |
| Repository list | Shows repositories the user can access | GET `/api/repositories` | Page and page size | Paged repositories |
| Repository details | Opens one repository | GET `/api/repositories/{id}` | Repository ID | Repository details |
| Check repository | Checks a repository before adding it | POST `/api/repositories/validate` | Repository URL | Access result and details |
| Add repository | Saves a repository | POST `/api/repositories` | Repository URL | New repository |
| Remove repository | Removes a repository | DELETE `/api/repositories/{id}` | Repository ID | Empty success |
| Branch list | Shows branches available to scan | GET `/api/repositories/{id}/branches` | Repository ID | Branch names, default marker, optional commit |
| Scan history | Lists past scans | GET `/api/scans` | Page, page size, optional repository ID | Paged scans |
| Scan details | Opens one scan | GET `/api/scans/{id}` | Scan ID | Scan details |
| Start scan | Starts security checks for a chosen branch | POST `/api/scans` | Repository ID and branch | New scan |
| Scan progress | Reports scan progress | GET `/api/scans/{id}/status` | Scan ID | Status and progress |
| Cancel scan | Stops a queued or running scan | POST `/api/scans/{id}/cancel` | Scan ID | Scan with `cancelled` status |
| Scan findings | Shows findings from one scan | GET `/api/scans/{id}/findings` | Scan ID and filters | Paged findings |
| Findings list | Shows findings across the workspace | GET `/api/findings` | Filters and page details | Paged findings |
| Finding details | Opens one finding | GET `/api/findings/{id}` | Finding ID | Finding details |
| Review finding | Saves a review status and note | PATCH `/api/findings/{id}` | Review status and optional note | Updated finding |
| Reports list | Lists available reports | GET `/api/reports` | Page and page size | Paged reports |
| Report details | Reports report preparation status | GET `/api/reports/{id}` | Report ID | Status and report details |
| Generate report | Starts or repeats a PDF report | POST `/api/reports` | Scan ID | Generating, ready, or failed report |
| Download report | Provides the finished PDF | GET `/api/reports/{id}/pdf` | Report ID | PDF file |
| Dashboard | Shows workspace totals and recent activity | GET `/api/dashboard/metrics` | Nothing | Counts and recent items |
| GitHub status | Shows whether GitHub is connected | GET `/api/integrations/github` | Nothing | Connection status |
| Connect GitHub | Connects GitHub | POST `/api/integrations/github` | Optional connection details | Connection status |
| Disconnect GitHub | Removes the GitHub connection | DELETE `/api/integrations/github` | Nothing | Connection status |
| Notification settings | Reads notification choices | GET `/api/users/me/settings` | Nothing | Completion and failure choices |
| Save notification settings | Saves notification choices | PUT `/api/users/me/settings` | Completion and failure choices | Updated choices |

`cancelled` is a new scan status beyond the four statuses in the requirements document—queued, running, completed, and failed—so the back end must support it explicitly.

## 6. Decisions made, rejected, and deferred

### Made

- Use one central data service so each feature has one clear future server connection.
- Let the system, not the user, set scan and report status.
- Allow cancellation only for queued or running scans.
- Use Rescan for failed, cancelled, and completed runs, with the previous branch selected first.
- Use PDF reports with browser preview and download.
- Keep account-recovery responses neutral so an email address cannot be tested for account existence.
- Keep development-only controls behind an explicit switch.

### Rejected or removed

- Fake report completion controls.
- Sample user management and role editing.
- Sample repository-access administration.
- Internal state exploration in normal Settings.
- Markdown report export.

### Deferred

- Server-side authorization and the final session-cookie and sign-in-error contract.
- Real GitHub OAuth and token handling.
- Real email delivery and reset-token issuance.
- AI explanation scope and how uncertainty is shown.
- Finding false-positive permissions and audit history.

Questions for the product team:

- Is sign-up open to everyone, invite-only, or created by an administrator?
- How much explanation should AI provide, and what evidence must always appear beside it?
- Who may mark a finding as a false positive, and what record must be kept?
- How should sessions expire, refresh, and respond when the server says a user is no longer signed in?

## 7. Known limitations

- The product still runs on sample data; no real server, scanner, GitHub account, email service, or AI service is connected.
- Report content and PDF creation are represented by sample behavior until the server is built.
- Workspace switching, the notification panel, command search, and notification switches in the shell are cosmetic or sample-backed in this front-end scope.
- The browser cannot enforce real permissions; the server must do that.
- Development performance results are machine-dependent. In the recorded sample, Turbopack improved `/repositories` warm and first visits but made the cold `/dashboard` compile slower; production was already fast.
- Lint has no errors but reports 17 warnings, mainly image optimization suggestions and unused imports or parameters.

## 8. How to check the work

1. Open the site while signed out. Confirm `/login` is shown and `/dashboard` sends you back to sign in.
2. Create an account on `/signup`, then confirm the workspace opens.
3. Sign out from the account menu and sign in again with the new account. Enter a wrong password once and confirm an inline error appears.
4. Add a repository and complete the repository check.
5. Start a scan, choose a branch other than the default when available, and confirm the selected branch appears in the scan.
6. While the scan is queued or running, choose Cancel scan, then choose Keep scanning or Cancel scan in the confirmation window.
7. Open a failed or cancelled scan and choose Rescan. Confirm the previous branch is preselected and can be changed.
8. Open a completed scan report, start report creation, wait for Ready, preview the PDF, and download it.
9. Force or use a failed report case, then choose Generate again.
10. Use Forgot password, submit an email, and confirm the neutral message. Open `/reset-password?token=valid-reset-token`, set a password, and try `expired-reset-token` to confirm the error state.
11. Open Settings and confirm there are no Users, role, repository-access preview, or state-explorer controls unless development tools were deliberately enabled.

## 9. Technical appendix

### Configuration and dependencies

- Created `eslint.config.mjs` using ESLint flat configuration with `eslint-config-next` Core Web Vitals and TypeScript rules.
- Changed `package.json` so `lint` runs `eslint .` without a prompt.
- Added approved development dependencies `eslint` and `eslint-config-next`; `package-lock.json` was updated.
- Existing development configuration uses `next dev --turbopack`, removes the custom development `splitChunks` setting, enables strict mode, and optimizes `lucide-react` imports.

### Application files created or changed

- Authentication: `src/app/auth.tsx`, `src/app/login/page.tsx`, `src/app/signup/page.tsx`, `src/app/reset-password/page.tsx`.
- Workspace screens: `src/app/dashboard.tsx`, `src/app/repositories.tsx`, `src/app/scans.tsx`, `src/app/findings.tsx`, `src/app/reports.tsx`, `src/app/settings.tsx`, `src/app/shell.tsx`, `src/app/components.tsx`.
- Service layer: `src/lib/api/index.ts`, `src/lib/api/hooks.ts`, `src/lib/api/endpoints.ts`, `src/lib/api/mock/services.ts`, `src/lib/api/mock/persist.ts`, `src/lib/api/QueryProvider.tsx`.
- Types and status: `src/types/index.ts`, `src/lib/scan-status.ts`, `src/lib/security-model.ts`, `src/app/data.ts`.
- Removed: `src/app/store.tsx` and the old `src/app/report-export.ts`.

### Documentation files

- Updated `docs/18-api-integration-guide.md`, `docs/19-performance-report.md`, and `docs/user-flows/05-review-findings.md`.
- The documentation set also includes the system walkthrough, action inventory, requirements traceability, document conflicts, data-model reconciliation, backend service breakdown, open questions, and front-end implementation specification.

### Actual verification results

- `npx tsc --noEmit`: passed with no output.
- `npm run lint`: passed with 0 errors and 17 warnings.
- `npm test`: 1 test file passed; 17 tests passed; 0 failed.
- `npm run build`: compiled successfully; lint/type checking passed; 15 static pages generated; 19 routes listed in the final route table. Build warnings were the same 17 lint warnings. Next.js also reported the existing `optimizePackageImports` experimental setting.
- Cleanup search `rg -n "setRole|useSetRole|setRepositoryAccess|DEMO_EMAIL|Complete demo" src`: no matches.
- Storage search `rg -n "localStorage|sessionStorage" src --glob '!src/lib/api/mock/**'`: only `src/test/api.test.ts` test stubs matched.
