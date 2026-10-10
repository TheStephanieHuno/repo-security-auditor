# Repo Security Auditor - System Walkthrough

## 1. Executive Summary
The **Repo Security Auditor** is a Next.js 15 application designed to provide an evidence-backed security review and vulnerability management dashboard. Currently, the application is **front-end only**, fully mocked using a React Context store (`src/app/store.tsx`) and `localStorage` to simulate a complete application state with fake data (`src/app/data.ts`). There is no real backend API, database, or authentication mechanism. The biggest gaps are the total absence of real data-fetching, a complete lack of server-side validation/schema definitions (no Zod/react-hook-form), and no real authentication layer.

## 2. Project Overview
- **Project Name:** Repo Security Auditor
- **Domain:** Security review, repository scanning, and vulnerability management.
- **Framework:** Next.js 15.2.0 (App Router), React 19.
- **Language:** TypeScript.
- **Tech Stack:** 
  - UI Libraries: `@base-ui/react`, `lucide-react`, `shadcn` (components).
  - Styling: Tailwind CSS v4 (`@tailwindcss/postcss`), `clsx`, `tailwind-merge`, `class-variance-authority`, `tw-animate-css`.
  - State Management: React Context with `localStorage` persistence.
  - Utilities: `sonner` (toasts), `next-themes` (dark mode).
- **Missing Dependencies:** Data-fetching (`SWR`/`React Query`/`axios`), Form handling (`react-hook-form`), Schema validation (`zod`/`yup`), Authentication (`next-auth`/etc.).
- **Unused Dependencies:** None immediately obvious, though `shadcn` indicates raw components that are mixed with custom `@base-ui/react` primitives.
- **Config Files:** `next.config.ts` (splitChunks disabled in dev server), `tsconfig.json` (strict mode), `package.json`. No `.env` or Docker files are present.

## 3. Folder Structure
- `/src/app` - Contains the Next.js App Router structure and primary domain components.
  - `/(dashboard)` - Route group for the authenticated application shell.
  - `/login` - Authentication routes.
  - `*.tsx` - Flat structure for feature components (`auth.tsx`, `dashboard.tsx`, `repositories.tsx`, etc.).
- `/src/components/ui` - Reusable Base UI and Tailwind primitive components (buttons, dialogs, inputs).
- `/src/lib` - Utility functions (`utils.ts` for Tailwind merge, `router.tsx` for custom navigation wrappers).
- `/public` - Static assets (`assets/48bdb.svg`, `favicon.ico`).

## 4. Route & Screen Inventory
| Route | File path | Screen purpose | Layout used | Auth needed? | Implementation status |
|---|---|---|---|---|---|
| `/` | `src/app/page.tsx` | Root redirect to dashboard | `RootLayout` | N/A | Fully functional (Redirect) |
| `/login` | `src/app/login/page.tsx` | Authentication page | `RootLayout` | No | Partially wired (Mock Auth) |
| `/dashboard` | `src/app/(dashboard)/dashboard/page.tsx` | Security Overview | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/repositories` | `src/app/(dashboard)/repositories/page.tsx` | Repositories list | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/repositories/new` | `src/app/(dashboard)/repositories/new/page.tsx` | Add repository flow | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/repositories/[id]` | `src/app/(dashboard)/repositories/[id]/page.tsx` | Repository details | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/repositories/[id]/scan` | `src/app/(dashboard)/repositories/[id]/scan/page.tsx` | Repository scanner trigger | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/scans` | `src/app/(dashboard)/scans/page.tsx` | Scan run history | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/scans/[id]` | `src/app/(dashboard)/scans/[id]/page.tsx` | Individual scan results | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/scans/[id]/findings` | `src/app/(dashboard)/scans/[id]/findings/page.tsx` | Scan findings tab view | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/scans/[id]/findings/[findingId]`| `src/app/(dashboard)/scans/[id]/findings/[findingId]/page.tsx` | Finding inspection | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/findings` | `src/app/(dashboard)/findings/page.tsx` | Workspace findings view | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/reports` | `src/app/(dashboard)/reports/page.tsx` | Security reports catalog | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/reports/[id]` | `src/app/(dashboard)/reports/[id]/page.tsx` | Security report review | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/settings` | `src/app/(dashboard)/settings/page.tsx` | Workspace settings | `DashboardLayout` | Yes | Partially wired (Mock Data) |
| `/help` | `src/app/(dashboard)/help/page.tsx` | Documentation | `DashboardLayout` | Yes | Partially wired (Mock Data) |

**Missing Screens:** Global `not-found.tsx` is missing (404s fall back to Next.js default). Registration and Password Reset flows are simulated in settings/auth components but lack dedicated routes.

## 5. Component Inventory
**UI Primitives (`src/components/ui`):**
- `badge.tsx`, `button.tsx`, `card.tsx`, `checkbox.tsx`, `dialog.tsx`, `input.tsx`, `progress.tsx`, `skeleton.tsx`, `sonner.tsx`, `switch.tsx`, `table.tsx`, `tabs.tsx`.
- **Props/State:** These are stateless pure presentation components built on `@base-ui/react`.

**Feature Components (`src/app/*.tsx`):**
- `auth.tsx` (Login form, holds local form state).
- `dashboard.tsx` (Metrics charts, stat cards, uses mock store).
- `findings.tsx` (Findings list, finding detail view, filters).
- `reports.tsx` (Reports list, PDF generation placeholder).
- `repositories.tsx` (Repository management, scanner triggering).
- `scans.tsx` (Scan history, real-time simulated scan progress).
- `settings.tsx` (User profile, github integration).
- `shell.tsx` (App shell layout, sidebar navigation, topbar).
- `store.tsx` (Global state provider, localStorage sync).
- `components.tsx` (Shared domain components like `EmptyState`).

## 6. Navigation & Link Audit
All navigation is currently handled via a custom Next.js router wrapper (`src/lib/router.tsx`) and standard links.
All links discovered (`/dashboard`, `/settings`, `/scans`, `/repositories`, etc.) are **Valid** and map to existing Next.js routes. No dead links (`#`) or `javascript:void(0)` were found in the codebase.
- **Valid Links:** ~20 (Sidebar navigation, breadcrumbs, action links).
- **Broken/Dead Links:** 0.

## 7. Interactive Element Audit
- **Forms:** Login (`auth.tsx`), Add Repository (`repositories.tsx`), Settings Updates (`settings.tsx`).
- **Buttons:** Scan triggers, status toggles, layout toggles (sidebar expand/collapse).
- **Status:** **Mock/local-state only**. Every interactive element is wired to `src/app/store.tsx` or local React state. There are no API handlers or empty `console.log` handlers. All interactivity executes fully simulated logic (e.g., simulating a 20-second scan progress bar).

## 8. Forms & Validation
- **Validation Strategy:** Client-side only using native HTML validation or basic React state checks.
- **Missing:** No robust validation schema (like Zod) for inputs. Password complexity rules, repository URL format validation, and robust API error handling are missing.

## 9. Data Layer & Mock Data
The entire application runs on mock data defined in `src/app/data.ts`.
- **Entities Inferred:**
  - `Repository` (id, name, description, language, branch, commit, visibility, connected, owner, url, access).
  - `Scan` (id, repoId, status, date, duration, progress, stage, findings).
  - `Finding` (id, repoId, title, severity, category, confidence, file, line, scanner, description, remediation).
  - `User/Profile` (name, email, role).
- **Data Calls:** None. Zero `fetch`, `axios`, or SWR calls exist.

## 10. Required Back-End Surface (Inferred)
| Feature | Endpoint (Method + Path) | Purpose |
|---|---|---|
| Auth | `POST /api/auth/login` | Authenticate user and return session/token |
| Auth | `POST /api/auth/logout` | Terminate session |
| User | `GET /api/users/me` | Fetch current user profile and role |
| Repositories | `GET /api/repositories` | List connected repositories |
| Repositories | `POST /api/repositories` | Add/Connect a new repository |
| Scans | `GET /api/scans` | List scan history |
| Scans | `POST /api/scans/trigger` | Initiate a new vulnerability scan |
| Scans | `GET /api/scans/:id/status` | Polling endpoint for scan progress |
| Findings | `GET /api/findings` | Fetch vulnerabilities with filtering/pagination |
| Findings | `PATCH /api/findings/:id` | Update finding status (e.g., mark False Positive) |
| Reports | `POST /api/reports/export` | Generate and download PDF security report |

## 11. Authentication, Authorization & Roles
- **Auth Screens:** `/login`.
- **Implementation:** Simulated via `sessionStorage` and `localStorage` in `src/app/store.tsx`.
- **Roles:** The UI mentions "Developer" roles and permissions, but all access checks (`isRestricted`) are purely client-side simulation. No route-level middleware protection exists (e.g., Next.js `middleware.ts` is absent).

## 12. State Management & Global Concerns
- **State Management:** React Context (`StoreProvider` in `store.tsx`).
- **Theming:** `next-themes` (Dark/Light mode fully implemented).
- **Notifications:** `sonner` toasts implemented.
- **Loading/Empty States:** Fully implemented using `components.tsx` (`EmptyState`, skeleton loaders).
- **Missing:** Server-side SEO metadata is basic (only in `layout.tsx`). No Analytics.

## 13. UX States & Edge Cases Missing
- **Real Loading States:** Currently using CSS animations or hardcoded `setTimeout` delays. Needs integration with real Promises.
- **API Error States:** Unhandled. The UI doesn't account for 500s, 403s, or network timeouts.
- **Pagination:** Findings lists might grow massive. Server-side pagination is not accounted for in the UI.

## 14. Quality, Performance & Security Observations
- **Code Quality:** Excellent. The codebase is clean, well-typed (TypeScript), and modular. No `any` types or `TODO`/`FIXME` comments were found.
- **Responsiveness:** Highly responsive, utilizes Tailwind mobile-first breakpoints.
- **Accessibility:** Uses `@base-ui/react` primitives which are generally highly accessible.
- **Security:** As it's 100% client-side mock data right now, no direct API security vulnerabilities exist, but it exposes the entire "database" in the client bundle.
- **Performance:** Client-side mock data makes it fast, but migrating to a real backend will require careful fetching strategies to maintain this performance.

## 15. Open Questions
1. **Authentication:** Will we use NextAuth.js, Supabase Auth, Auth0, or a custom JWT solution?
2. **Database:** What is the target database (PostgreSQL, MongoDB) and ORM (Prisma, Drizzle)?
3. **Scan Execution:** How will the actual repository scans be triggered? Do we integrate with GitHub Actions, an external CI/CD tool, or our own worker nodes?
4. **Data Synchronization:** Do we need webhooks to sync repository changes from GitHub/GitLab?

## 16. Master Issue Register
| ID | Category | Location | Description | Severity |
|---|---|---|---|---|
| 001 | API | Entire App | No real backend APIs; entirely mocked in `data.ts`. | Blocker |
| 002 | Auth | `src/app/auth.tsx` | Authentication is simulated via localStorage. Needs real auth provider. | Blocker |
| 003 | Security | App Router | Missing `middleware.ts` to protect dashboard routes from unauthenticated users. | High |
| 004 | Data | `src/app/store.tsx` | State is managed client-side. Will not scale for real data. Needs React Query or SWR. | High |
| 005 | Form | `src/app/*.tsx` | Lack of robust form validation (e.g., Zod) on inputs. | Medium |
| 006 | UX | `src/app` | Missing `not-found.tsx` for global 404 handling. | Low |

## 17. Counts Summary
- **Screens:** 15 existing routes mapped.
- **Components:** 12 UI primitives, 10 feature components.
- **Links:** ~20 (All Valid, 0 Broken, 0 Dead).
- **Interactive Elements:** Fully mock-implemented (0 empty handlers).
- **Forms:** 3 main forms.
- **Inferred Endpoints:** ~11 required.
- **Inferred Entities:** 4 core models (User, Repository, Scan, Finding).

## 18. Coverage Statement
- **Reviewed:** `package.json`, `next.config.ts`, `tsconfig.json`, `src/app/**`, `src/components/ui/**`, `src/lib/**`.
- **Skipped:** `node_modules`, `.next`, `public` (binary assets).
- **Method:** Exhaustive code reading and search heuristics using directory listings and file analysis tools. All findings are accurate based on current file states.
