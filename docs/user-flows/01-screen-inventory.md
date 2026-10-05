# Screen inventory

## Global shell and authentication

| ID | Route | File | Purpose | Data/source | Entry/exit and visibility | States |
|---|---|---|---|---|---|---|
| S-01 | / | src/app/page.tsx:1-5 | Select the authenticated or unauthenticated entry route. | useSession in src/lib/api/hooks.ts:30-35. | Public; redirects to /dashboard when a session exists, otherwise /login. | Session loading renders nothing; authenticated and unauthenticated redirects. |
| S-02 | /login | src/app/login/page.tsx:1-11; src/app/auth.tsx:18-224 | Sign in or open the demo workspace. | useSession/useLogin and api.DEMO_EMAIL; API services in src/lib/api/index.ts:45-65. | Public; logout and 401 flows can enter here; authenticated users redirect to /dashboard. | Loading/authenticated; invalid credentials; network scenario; forgot-password dialog; password reveal; pending submit. |
| S-03 | /signup | src/app/signup/page.tsx:1-6; src/app/auth.tsx:229-264 | Register a new account. | useSession/useRegister and Zod/react-hook-form schema in src/app/auth.tsx:229-240. | Public; authenticated users redirect to /dashboard; sign-in link exits to /login. | Loading/authenticated; inline field errors; pending submit; error toast. |
| S-04 | Any dashboard route | src/app/(dashboard)/layout.tsx:1-26 | Protect private routes and render Shell. | useSession and Shell. | Logged-in users see the route; unauthenticated users go to /login?redirect=<path>. | Session skeleton, redirect, protected content. |
| S-05 | Any dashboard route | src/app/shell.tsx:80-640 | Provide sidebar, top bar, search, theme, notifications, profile, and logout. | useTheme, useSession, repository/scan/finding hooks, useLogout at src/app/shell.tsx:87-109. | All private screens enter through this shell; sidebar/topbar/profile links leave it. | Mobile menu, command dialog, theme toggle, notification panel, profile menu, session loading. |
| S-06 | Global error | src/app/error.tsx:1-17 | Recover from an unexpected render/route error. | None. | Next error boundary; Return to dashboard exits to /dashboard. | Error message and recovery link. |
| S-07 | Global loading | src/app/loading.tsx | Show route-loading UI. | Static loading UI. | Automatic during route transitions. | Loading only. |

## Main route screens

| ID | Route | File | Purpose and visible UI | Data source | Entry/exit and states |
|---|---|---|---|---|---|
| S-08 | /dashboard | src/app/dashboard.tsx:51-432 | KPI cards, severity distribution, recent scans, repository cards, security alert, start-scan and add-repository actions. | useRepositories/useScans/useFindings. | Shell/root/dashboard links; exits to repositories, findings, scans, reports, repository/finding/scan detail and dialogs. Loading/empty/error are handled by PageState. |
| S-09 | /repositories | src/app/repositories.tsx:71-345 | Search, repository filters, cards/table, latest status, add repository, scan, overflow actions. | useRepositories/useScans/useFindings at :73-77. | Shell/dashboard/empty-state links; repository cards open detail. Loading, empty, filtered empty, overflow and scan dialogs. |
| S-10 | /repositories/new | src/app/repositories.tsx:383-735 | GitHub URL form, validation preview, metadata, permission confirmation, add action. | useRepositories/useValidateRepository/useCreateRepository. | Add-repository CTAs and breadcrumb; success navigates to repository detail. Missing, unsupported, denied, offline, pending, duplicate, and permission states. |
| S-11 | /repositories/[id] | src/app/repositories.tsx:737-1110 | Repository identity, metadata, overview, scans, findings, reports tabs, latest scan, severity summary, GitHub link. | useRepositories/useScans/useFindings at :741-743. | Repository cards, dashboard, deep links; tabs and scan/report/finding links. Loading, not-found, forbidden, no-scan, no-finding, and dialog states. |
| S-12 | /repositories/[id]/scan | src/app/(dashboard)/repositories/[id]/scan/page.tsx:1-11 | Repository detail with ScanDialog initially open. | Repository detail plus useRepositoryBranches in src/app/components.tsx:716-866. | Scan CTAs/direct URL; dialog cancel returns to detail, submit navigates to scan detail. Branch loading/error/one-branch disabled states. |
| S-13 | /scans | src/app/scans.tsx:46-323 | Search, status/date/repository filters, scan history table/cards, statuses, branches, findings/report links. | useRepositories/useScans/useFindings at :64-66. | Shell/dashboard/repository links; start-scan dialog. Loading, empty, filtered empty, dialog, and read-only status states. |
| S-14 | /scans/[id] | src/app/scans.tsx:327-1067 | Progress/stages, status, branch/commit, activity, scanner panels, findings, history, tabs, report/rescan/retry/cancel controls. | useRepositories/useScans/useFindings at :330-332; scan status polling in src/lib/api/hooks.ts:195-211. | History/dashboard/repository/finding/report/deep links. Queued, running, completed with findings, clean, failed, partial, polling and retry states. |
| S-15 | /scans/[id]/findings | src/app/(dashboard)/scans/[id]/findings/page.tsx:1-11 | Findings list scoped to a scan. | FindingsList and scan findings API. | Scan detail tab/link; back to scan. Loading, empty, filtered empty, error, and finding links. |
| S-16 | /scans/[id]/findings/[findingId] | src/app/(dashboard)/scans/[id]/findings/[findingId]/page.tsx:1-11 | Finding evidence, context, remediation, AI state, and human triage. | FindingDetail and useFinding/useUpdateFinding. | Finding links and back links. Loading/not-found, AI unavailable/retry, context/evidence sections, status dialog, pending/error/success. |
| S-17 | /findings | src/app/findings.tsx:80-555 | Workspace findings search, severity/category/scanner/status/confidence filters, sort, pagination, table/cards and links. | useRepositories/useScans/useFindings at :88-90. | Shell/dashboard/repository/scan links. Loading, empty, filtered empty, filter drawer, pagination and API error. |
| S-18 | Finding detail state | src/app/findings.tsx:560-1230 | Shared detail implementation for dynamic finding route: breadcrumb, evidence, context carousel, remediation, AI explanation and triage. | useFindings and useUpdateFinding at :563-569. | Dynamic route and finding links; same detail states as S-16. |
| S-19 | /reports | src/app/reports.tsx:39-190 | Search, coverage filter, report list/cards, status, branch, view and Download PDF. | useReports/useRepositories/useScans/useFindings. | Shell/dashboard/scan/repository links; empty CTA to repositories. Loading, empty, filtered empty, generating/ready/failed. |
| S-20 | /reports/[id] | src/app/reports.tsx:200-620 | PDF report metadata, branch, findings/severity, scanner coverage, limitations, view scan and Download PDF. | useReport polling, scan/repository/finding hooks. | Report list and deep links. Loading/not-found, Generating PDF, failed/retry, ready, download pending/success/error. |
| S-21 | /settings | src/app/settings.tsx:101-335 | Profile fields, save, role display, password dialog and sign-out dialog. | useSession/useUpdateProfile/useUpdatePassword/useLogout. | Shell profile/sidebar; settings tabs. Pending, success, validation and error states. |
| S-22 | /settings?tab=github | src/app/settings.tsx:337-400 | GitHub connected badge, repository count, permission dialog, connect/disconnect. | useGitHubStatus/useGitHubConnect/useGitHubDisconnect. | Settings tab and scan/repository recovery link. Loading, connected/disconnected, pending, toast success/error. |
| S-23 | /settings?tab=notifications | src/app/settings.tsx:401-445 | Completion and failure notification switches. | useSettings/useUpdateSettings. | Settings tab. Loading, disabled while saving, success/error toast. |
| S-24 | /settings?tab=users | src/app/settings.tsx:447-499 | Sample users table and role preview. | Local demo preview state; session role controls visibility. | Administrator-only tab. Hidden for other roles; local sample role edits. |
| S-25 | /settings?tab=demo | src/app/settings.tsx:501-735 | Role selector, repository access preview, state explorer, reset demo. | useSetRole/useSetRepositoryAccess/useResetDemo. | Settings tab and internal deep-link buttons. Pending/reset, role/access preview, state links. |
| S-26 | /help | src/app/(dashboard)/help/page.tsx; src/app/settings.tsx:755-840 | Product workflow, scanner/report guidance, limitations and repository CTA. | Static content. | Shell sidebar/settings links; repository CTA. |

## Shared overlays

| ID | Component | File and behavior |
|---|---|---|
| S-27 | ScanDialog | src/app/components.tsx:716-866; repository selector, searchable branch input, scanner checklist, cancel/start, branch loading/error/one-branch disabled, GitHub and queue errors. |
| S-28 | DownloadReport | src/app/components.tsx:866-905; generate/download PDF, spinner, success/error toast. |
| S-29 | Repository overflow/delete | src/app/repositories.tsx:210-335; view, report, delete, confirm/cancel. |
| S-30 | Repository permission | src/app/repositories.tsx:580-630; read-only permission confirmation. |
| S-31 | Findings filters | src/app/findings.tsx:515-535; apply, clear, close. |
| S-32 | Finding status | src/app/findings.tsx:1170-1230; Reviewed/Resolved/False positive and optional note. |
| S-33 | Settings dialogs | src/app/settings.tsx:670-735; password, sign-out, reset confirmation. |
| S-34 | Shell overlays | src/app/shell.tsx:150-350; command search, mobile menu, profile, workspace and theme/notification controls. |

