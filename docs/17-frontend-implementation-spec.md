# Frontend Implementation Spec: Repo Security Auditor

## 1. Exhaustive Inventory of Interactive Elements

Through AST-like parsing of all `.tsx` components in `src/`, exactly 143 interactive navigation and mutation elements were identified.

**Classification Counts:**
- Works UI-only: 104
- Mock mutation: 39 (State updates and store commits)
- Fake delay: 0 explicitly matched without mock mutations, though `setTimeout` is heavily used within those mock mutations.
- Empty / No handler / Broken link: 0 (There are NO elements mapped to empty callbacks `() => {}`, `javascript:void(0)`, or broken `href="#"` fragments).

*As requested, listing every element classified Empty, No handler, or Broken link:*
- **NONE FOUND**. The UI implementation correctly uses internal routing state (`LinkButton to=`) and modal states.

## 2. API Placeholder Registry

| Function | Resource | HTTP Method + Path | Request Type | Response Type | Called From (file:line) | Replaces |
|---|---|---|---|---|---|---|
| `login` | Auth | `POST /api/auth/login` | `LoginRequest` | `AuthResponse` | `auth.tsx:100` | `signIn(true)` / store user |
| `logout` | Auth | `POST /api/auth/logout` | `None` | `None` | `shell.tsx:595`, `settings.tsx:275` | `setSignout(true)` |
| `getSession` | Auth | `GET /api/auth/session` | `None` | `User` | `providers.tsx` | Context `store.user` |
| `updatePassword` | Users | `PUT /api/users/me/password` | `PasswordUpdateRequest` | `None` | `settings.tsx:182` | `setPasswordOpen(true)` |
| `getRepositories` | Repositories | `GET /api/repositories` | `None` | `Paginated<Repository>` | `repositories.tsx:180` | `store.repositories` |
| `getRepository` | Repositories | `GET /api/repositories/{id}` | `None` | `Repository` | `repositories.tsx:645` | `store.repositories.find()` |
| `createRepository` | Repositories | `POST /api/repositories` | `RepositoryCreate` | `Repository` | `repositories.tsx:441` | `store.addRepository()` |
| `validateRepository` | Repositories | `POST /api/repositories/validate` | `RepositoryValidate` | `ValidateResponse` | `repositories.tsx:497` | `setTimeout` simulation |
| `deleteRepository` | Repositories | `DELETE /api/repositories/{id}` | `None` | `None` | `repositories.tsx:253` | `store.removeRepository()` |
| `getScans` | Scans | `GET /api/scans` | `None` | `Paginated<Scan>` | `scans.tsx:120` | `store.scans` |
| `getScan` | Scans | `GET /api/scans/{id}` | `None` | `Scan` | `scans.tsx:325` | `store.scans.find()` |
| `triggerScan` | Scans | `POST /api/scans` | `ScanTrigger` | `Scan` | `repositories.tsx:876` | `store.addScan()` + `setTimeout` |
| `getScanStatus` | Scans | `GET /api/scans/{id}/status` | `None` | `ScanStatus` | `scans.tsx:380` | Polling replacement |
| `getFindings` | Findings | `GET /api/findings` | `FindingQuery` | `Paginated<Finding>` | `findings.tsx:210` | `store.findings` |
| `getFinding` | Findings | `GET /api/findings/{id}` | `None` | `Finding` | `findings.tsx:812` | `store.findings.find()` |
| `updateFindingStatus`| Findings | `PATCH /api/findings/{id}` | `FindingUpdate` | `Finding` | `findings.tsx:750` | `store.updateFinding()` |
| `getReports` | Reports | `GET /api/reports` | `None` | `Paginated<Report>` | `reports.tsx:110` | `store.reports` |
| `generateReport` | Reports | `POST /api/reports` | `ReportCreate` | `Report` | `reports.tsx:217` | `store.addReport()` |
| `getDashboard` | Dashboard | `GET /api/dashboard/metrics` | `None` | `DashboardMetrics`| `dashboard.tsx:55` | Derived from context |
| `githubConnect` | Integrations | `POST /api/integrations/github` | `GitHubConnect` | `None` | `settings.tsx:450` | Mock toggle |

## 3. Complete Screen List

- `src/app/auth.tsx` (Login, password reset simulation)
- `src/app/dashboard.tsx` (Dashboard overview, metrics, latest scans)
- `src/app/repositories.tsx` (List, add, detail, validation flow)
- `src/app/scans.tsx` (History, detail, progress)
- `src/app/findings.tsx` (List, filters, sort, review actions, detail)
- `src/app/reports.tsx` (List, detail, export)
- `src/app/settings.tsx` (Profile, password update, github integration)
- `src/app/shell.tsx` (Sidebar, topbar, breadcrumbs, search)
- `src/app/help.tsx` (Help / Docs page)
- `src/app/components.tsx` (Reused UI parts)

## 4. API Client (Fetch)

The API client in `src/lib/api/client.ts` will strictly use **native `fetch`** (no Axios). It will include a fetch wrapper that handles:
- Base URL injection.
- JSON serialization/deserialization.
- Automatic throwing of custom `ApiError` for non-2xx responses.
- 401 interception (see section 7).

## 5. Dev Dependencies

| Dependency | Justification |
|---|---|
| `vitest` | Ultra-fast unit testing framework that integrates seamlessly with our Vite/Next.js environment. |
| `@testing-library/react` | Required for mounting and interacting with React components during tests. |
| `@testing-library/jest-dom` | Provides custom DOM element matchers (e.g., `toBeInTheDocument()`, `toHaveTextContent()`) for clean assertions. |
| `happy-dom` | A fast, lightweight DOM simulator for Node.js to run React component tests without a real browser (chosen over jsdom for speed). |

## 6. Mock Mode & Persistence

**Mock Mode Behavior**: The application must behave exactly as it does today when `NEXT_PUBLIC_API_MODE=mock`. 
- `localStorage` persistence will be completely removed from `store.tsx` and moved **into the mock adapters** inside `src/lib/api/mock/*.ts`.
- The mock service layer will load the seed data from `data.ts`, persist modifications to `localStorage`, and return responses wrapped in artificial promises with simulated latency.
- **Scan Progress**: The simulated scan progression will be managed inside `mock/scans.mock.ts`. When a scan is triggered, the mock adapter stores the start time. When the UI polls `getScanStatus`, the mock adapter calculates the current `stage` based on the elapsed time since start, advancing linearly up to stage 10. The UI handles polling using React Query's `refetchInterval`, entirely ignorant of whether the backing API is live or mock.

## 7. Session & 401 Handling

- **Session Ownership**: The session and current user will no longer live in the raw `store.tsx`. They will be managed by a custom hook `useAuth()` backed by the `getSession` API placeholder.
- **401 Redirects**: The native `fetch` wrapper in `src/lib/api/client.ts` checks every response. If `res.status === 401`, it immediately triggers a redirect to `/login?redirect={encodeURIComponent(window.location.pathname)}`. The `useAuth` hook will detect this and clear internal cache.

## 8. Pagination, Filters, and Sorting

- **Pagination Approach**: Offset-based pagination will be used.
- **URL Sync**: All list views (Findings, Repositories, Scans) will track `page`, `page_size` (snake_case), `sort`, `direction`, and `search` (with debounce) entirely within the URL query parameters.
- **Response Envelope**: All list endpoints expect: `{{ items: T[], total: number, page: number, page_size: number }}`.

## 9. Missing System Elements to Add

- **Error Boundaries**: Create `error.tsx` (graceful error states with "Try again" retry buttons).
- **Loading UI**: Create `loading.tsx` to automatically integrate the existing skeleton loaders.
- **Not Found**: Create `not-found.tsx` for 404s.
- **Toasts**: Add `sonner` toasts indicating success/failure for *every* mutation (e.g. "Finding reviewed successfully", "Failed to add repository").
- **UX**: All submit/action buttons must implement `disabled={{isPending}}` and show a loading spinner while React Query mutations are in-flight.
- **Polling Hook**: A custom `useScanPolling(scanId)` hook using React Query `refetchInterval` that automatically halts (`refetchInterval: false`) when the scan status reaches `Completed` or `Failed`.
- **Smoke Test**: A Vitest route smoke test that mounts the app and verifies navigation to every route without crashing.
- **API Guide**: Produce `docs/18-api-integration-guide.md` containing all placeholders.

## 10. Acceptance Criteria / Greps

Before completion, the following grep assertions must yield 0 results:
- `grep -r 'href="#"' src/` -> 0
- `grep -r 'javascript:void' src/` -> 0
- `grep -r 'onClick={{() => {{}}}}' src/` -> 0
- `grep -r 'console.log(' src/app` -> 0 (excluding valid error logs in client wrapper)
- `grep -r 'localStorage' src/app/` -> 0 (only allowed in `src/lib/api/mock/`)
- `grep -r 'from "../data"' src/app/` -> 0 (only mock adapters can import `data.ts`)

`tsc --noEmit`, ESLint, tests, and `next build` must pass without errors.
