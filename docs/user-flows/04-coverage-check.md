# Coverage check

## Counts

| Measure | Count | Basis |
|---|---:|---|
| Route entries | 17 | All page files under src/app, including /, /login, /signup, 12 dashboard routes, /settings, /help, and dynamic routes. |
| Screen/state records | 34 | S-01 through S-34 in 01-screen-inventory.md. |
| Transition records | 74 | T-001 through T-074 in 02-transition-inventory.md. |
| End-to-end flows | 15 | F-01 through F-15 in 03-user-flows.md. |
| Explicit unmapped items | 6 | Listed below. |
| Review findings | 18 | 5 Remove, 4 Merge, 4 Add, 3 Fix, 2 Clarify in 05-review-findings.md. |

## Route-to-flow coverage

| Route | Flow coverage |
|---|---|
| / | F-01 |
| /login | F-03, F-04, F-05 |
| /signup | F-02 |
| /dashboard | F-13 |
| /repositories | F-06, F-07 |
| /repositories/new | F-06 |
| /repositories/[id] | F-07, F-08 |
| /repositories/[id]/scan | F-08 |
| /scans | F-10 |
| /scans/[id] | F-09, F-10, F-12 |
| /scans/[id]/findings | F-11 |
| /scans/[id]/findings/[findingId] | F-11 |
| /findings | F-11 |
| /reports | F-12 |
| /reports/[id] | F-12 |
| /settings | F-05, F-14 |
| /help | F-15 |

The global error/loading states are covered by F-15 and the alternate/error sections of every data flow.

## Interactive coverage

All transition IDs T-001 through T-074 are represented in at least one flow, except the following items which are intentionally not independent end-to-end goals:

1. T-005 password reveal: presentation-only control.
2. T-014 theme toggle: presentation-only control.
3. T-015 overlay open/close: container behavior; contained links are separately covered.
4. T-049 disabled scan cancel: unsupported action documented as a dead control.
5. T-055 section/context controls: in-page presentation only.
6. T-073 browser back/forward: browser-owned behavior with no application handler.

## Cross-check against existing documentation

- docs/02-link-and-action-inventory.md is a useful prior pointer list but labels most entries “Works UI-only”; this inventory adds conditions, API calls, failure paths, query parameters, polling, dialogs, and keyboard behavior.
- docs/11-requirements-traceability.md claims access control through src/app/store.tsx. That store has since been removed; current access/session behavior is in src/app/(dashboard)/layout.tsx, src/app/shell.tsx, and src/lib/api hooks/mock adapters.
- docs/11-requirements-traceability.md calls report export an “Export Report Button”; current implementation is PDF generation/download, not markdown export.
- docs/11-requirements-traceability.md lists password reset as a settings form; current login forgot-password UI is a local preview and does not call an email/reset API.
- The referenced docs/source/ directory was not present in the repository. The available SRS/PRD files are under docs and root-level document assets; no additional source-folder comparison was possible.
- Existing route inventory and implementation differ where older documentation refers to store-backed sample data; current screens use src/lib/api hooks, while data.ts remains a mock fixture/presentation source.

## Reproducible search procedure

The inventory was checked with these commands from repository root:

    rg --files src/app | Sort-Object

    Get-ChildItem src -Recurse -File -Include *.ts,*.tsx |
      Select-String -Pattern 'export function|export default function|<Button|<Link|<LinkButton|navigate\(|router\.|redirect\(|useNavigate|useRouter|onClick=|onSubmit=|onChange=|TabsTrigger|Dialog|toast\.|setInterval|refetchInterval|window\.open|href='

    Get-ChildItem src -Recurse -File -Include *.ts,*.tsx |
      Select-String -Pattern 'use[A-Z][A-Za-z]+\(|api\.[A-Za-z]+|endpoints\.|fetch\('

    rg -n 'from "./data"|from "@/app/data"|useStore|localStorage|sessionStorage' src

    rg -n 'to=|href=|navigate\(|router\.|redirect\(|onClick=|onSubmit=|onChange=' src/app

The resulting route files, action locations, API hook/service calls, and existing link/action inventory were manually reconciled into S-*, T-*, and F-* records.

