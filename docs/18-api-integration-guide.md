# API integration guide

The front end uses `NEXT_PUBLIC_API_MODE=mock|live`. Mock mode supplies sample data; live mode is the single place where the future FastAPI calls are connected.

## Current placeholders

| Area | Method | Endpoint | Sends | Returns |
|---|---|---|---|---|
| Sign in | POST | `/api/auth/login` | Email and password | Access token response |
| Sign up | POST | `/api/auth/register` | Name, email, password | Access token response |
| Sign out | POST | `/api/auth/logout` | Nothing | Empty response |
| Current user | GET | `/api/users/me` | Nothing | User profile and session state |
| Request password reset | POST | `/api/auth/password-reset/request` | Email | Neutral empty response |
| Confirm password reset | POST | `/api/auth/password-reset/confirm` | Reset token and new password | Empty response or invalid/expired-token error |
| Update profile | PUT | `/api/users/me` | Name and email | Updated user |
| Change password | PUT | `/api/users/me/password` | Current and new password | Empty response |
| List repositories | GET | `/api/repositories` | Page and page size | Paged repository list |
| Repository details | GET | `/api/repositories/{id}` | Repository ID | Repository |
| Check repository | POST | `/api/repositories/validate` | Repository URL | Access and repository details |
| Add repository | POST | `/api/repositories` | Repository URL | Repository |
| Remove repository | DELETE | `/api/repositories/{id}` | Repository ID | Empty response |
| List branches | GET | `/api/repositories/{id}/branches` | Repository ID | Branch names, default marker, and optional commit |
| List scans | GET | `/api/scans` | Page, page size, optional repository ID | Paged scan list |
| Scan details | GET | `/api/scans/{id}` | Scan ID | Scan |
| Start scan | POST | `/api/scans` | Repository ID and selected branch | Scan |
| Scan progress | GET | `/api/scans/{id}/status` | Scan ID | Status and progress |
| Cancel scan | POST | `/api/scans/{id}/cancel` | Scan ID | Scan with `cancelled` status |
| Scan findings | GET | `/api/scans/{id}/findings` | Scan ID and filters | Paged finding list |
| List findings | GET | `/api/findings` | Filters and paging | Paged finding list |
| Finding details | GET | `/api/findings/{id}` | Finding ID | Finding |
| Update finding | PATCH | `/api/findings/{id}` | Review status and optional note | Updated finding |
| List reports | GET | `/api/reports` | Page and page size | Paged report list |
| Report details | GET | `/api/reports/{id}` | Report ID | Report status and metadata |
| Generate report | POST | `/api/reports` | Scan ID | Report with `generating`, `ready`, or `failed` status |
| Download report | GET | `/api/reports/{id}/pdf` | Report ID | PDF file |
| Dashboard | GET | `/api/dashboard/metrics` | Nothing | Dashboard counts and recent items |
| GitHub status | GET | `/api/integrations/github` | Nothing | Connection status |
| Connect GitHub | POST | `/api/integrations/github` | Optional connection details | Connection status |
| Disconnect GitHub | DELETE | `/api/integrations/github` | Nothing | Connection status |
| Get notification settings | GET | `/api/users/me/settings` | Nothing | Completion and failure preferences |
| Update notification settings | PUT | `/api/users/me/settings` | Completion and failure preferences | Updated preferences |

Every live branch is marked `PLACEHOLDER: connect to FastAPI` in the service layer. The back end will have the AI write the report content and render the PDF on the server; the front end only requests the report and PDF.

## Removed placeholders

Markdown report export, role editing, repository-access preview, state exploration, and demo-generation controls are not API contracts. Scan status and report status are controlled by the system; users cannot edit them directly.
