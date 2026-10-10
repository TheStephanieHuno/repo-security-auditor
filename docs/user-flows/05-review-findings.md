# Review findings and decisions

These are code-based findings for product/backend review. The approved implementation decisions are checked below.

| # | Type | Screen or flow | Evidence | Description | Recommendation | Priority | Decision |
|---:|---|---|---|---|---|---|---|
| 1 | Remove | Login forgot-password preview | src/app/auth.tsx:167-207 | Looks like recovery but only previews acceptance and sends no email. | Replace with real reset flow when backend contract exists, or label as prototype-only. | High | [ ] Approve [ ] Reject |
| 2 | Remove | Disabled cancel scan | src/app/scans.tsx:681-687 | Presents a cancel action that cannot be used. | Remove until cancellation API/status exists. | Med | [ ] Approve [ ] Reject |
| 3 | Remove | “Complete demo generation” | src/app/reports.tsx:277-290 | Mutates local URL state rather than report generation status. | Remove or replace with retry/generate API action. | High | [ ] Approve [ ] Reject |
| 4 | Remove | Sample users tab | src/app/settings.tsx:447-499 | Sample data and role preview are not workspace user management. | Remove from production navigation or explicitly mark demo-only. | Low | [ ] Approve [ ] Reject |
| 5 | Remove | Demo state explorer | src/app/settings.tsx:565-611 | Exposes internal QA scenarios to normal users. | Move to a development-only route/tool. | Low | [ ] Approve [ ] Reject |
| 6 | Merge | Scan entry points | src/app/shell.tsx:221; src/app/dashboard.tsx:164; src/app/repositories.tsx:204; src/app/scans.tsx:90 | Many buttons open the same ScanDialog. | Keep entry points but standardize one shared label and telemetry event. | Med | [ ] Approve [ ] Reject |
| 7 | Merge | Rescan/retry controls | src/app/scans.tsx:445,637,662,691,992 | Several labels/actions open the same new-scan path. | Use one Rescan action with branch preselection and clear failed/retry copy. | Med | [ ] Approve [ ] Reject |
| 8 | Merge | Report download buttons | src/app/scans.tsx:483; src/app/reports.tsx:149,325; src/app/components.tsx:866-905 | Same PDF action appears in multiple surfaces. | Keep locations, centralize status/toast/filename behavior in one component/hook. | Med | [ ] Approve [ ] Reject |
| 9 | Merge | Findings detail implementations | src/app/findings.tsx:560-1230 and scan finding wrappers | Global and scan-scoped detail share most UI. | Use one detail component with explicit scope/parent context. | Low | [ ] Approve [ ] Reject |
| 10 | Add | Real password recovery | src/app/auth.tsx:167-207 | No actual reset request or confirmation path. | Add request, token, success, expired-token, and retry states. | High | [ ] Approve [ ] Reject |
| 11 | Add | PDF preview | src/app/reports.tsx:320-365; src/app/components.tsx:866-905 | Report requirement calls for preview where design allows; current UI only downloads. | Add blob URL iframe/object with revoke-on-unmount. | Med | [ ] Approve [ ] Reject |
| 12 | Add | Scan cancellation | src/app/scans.tsx:681-687 | UI explicitly says cancellation is unsupported. | Add cancel mutation, cancelled status, confirmation, and polling stop behavior. | Med | [ ] Approve [ ] Reject |
| 13 | Add | Report lifecycle retry contract | src/app/reports.tsx:246-251; src/lib/api/hooks.ts:276-293 | Failed/retry UI does not call a dedicated retry/generate action. | Define idempotent generate/retry endpoint semantics. | High | [ ] Approve [ ] Reject |
| 14 | Fix | Report generation status | src/app/reports.tsx:277-290 | Current “Generating PDF” state is driven partly by URL demo state and scan status. | Drive entirely from Report status query: generating/ready/failed. | High | [ ] Approve [ ] Reject |
| 15 | Fix | Empty-state recovery | src/app/components.tsx:449-480; src/app/error.tsx:11 | Different empty/error screens use different recovery actions and copy. | Standardize loading/error/empty contracts and recovery CTA hierarchy. | Med | [ ] Approve [ ] Reject |
| 16 | Fix | Status label consistency | src/app/components.tsx:212-244; scan/report screens | Legacy statuses and canonical outcome labels coexist. | Use one system-owned outcome helper and mapping across all screens. | High | [ ] Approve [ ] Reject |
| 17 | Clarify | Access control model | src/app/(dashboard)/layout.tsx:15-23; src/lib/api/client.ts:45-75 | Client guard and 401 redirect exist, but backend cookie/middleware contract is pending. | Decide session cookie, 401 payload, public endpoints, and middleware rollout. | High | [ ] Approve [ ] Reject |
| 18 | Clarify | Branch/report backend contract | src/app/components.tsx:726-861; src/lib/api/index.ts report methods | Branch list, scan branch, PDF readiness, filename, and report ID relationships need backend agreement. | Freeze request/response schemas before FastAPI integration. | High | [ ] Approve [ ] Reject |

## Summary by decision type

Implementation decision: approve items 1–16 for this front-end scope. Items 17–18 remain open backend contract questions; cookie/middleware and server authorization are intentionally unchanged.

| Type | Count |
|---|---:|
| Remove | 5 |
| Merge | 4 |
| Add | 4 |
| Fix | 3 |
| Clarify | 2 |
| Total | 18 |

## Top ten recommendations

1. Define the authentication/session-cookie and 401 contract.
2. Replace the fake forgot-password preview with a real recovery contract.
3. Make report generation lifecycle API-driven and idempotent.
4. Add PDF preview or explicitly remove that expectation.
5. Remove or implement scan cancellation.
6. Standardize canonical scan/report status labels.
7. Freeze branch-selection and scanned-branch response schemas.
8. Remove demo-only state/user surfaces from production navigation.
9. Consolidate retry/rescan behavior and preserve the selected branch.
10. Standardize empty/error recovery and API failure copy.
