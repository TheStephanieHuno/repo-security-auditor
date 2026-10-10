# Transition inventory

This table records interactive elements and automatic transitions in the current implementation. Cosmetic rows only change presentation state or close an overlay.

| ID | From | Element | Source | Trigger/condition | Action | Result/API | Success/failure |
|---|---|---|---|---|---|---|---|
| T-001 | S-01 | Root route | src/app/page.tsx:1-5 | Session resolves | Redirect | useSession | Dashboard if authenticated; login otherwise. |
| T-002 | S-02 | Demo login buttons | src/app/auth.tsx:88-96,204-224 | Click | Login then navigate | useLogin | Dashboard; inline error. |
| T-003 | S-02 | Email login form | src/app/auth.tsx:108-116 | Submit | Login then safe redirect | useLogin | redirect query for a single-leading-slash path; otherwise dashboard; inline error. |
| T-004 | S-02 | Forgot password | src/app/auth.tsx:130-136 | Click | Open dialog | None | Preview/reset dialog; close returns to login. |
| T-005 | S-02 | Password eye | src/app/auth.tsx:152-160 | Click | Toggle input type | None | Cosmetic presentation change. |
| T-006 | S-02 | Reset preview form | src/app/auth.tsx:190-207 | Submit | Local dialog state | None | Confirmation preview; no email is sent. |
| T-007 | S-03 | Signup form | src/app/auth.tsx:241-254 | Valid schema submit | Register then safe redirect | useRegister | Destination path or dashboard; error toast. |
| T-008 | S-03 | Sign in link | src/app/auth.tsx:263-264 | Click | Navigate | None | Login with redirect preserved. |
| T-009 | Auth pages | Existing session guard | src/app/auth.tsx:51-55,246-250 | Session resolves | Redirect | useSession | Dashboard when already authenticated. |
| T-010 | S-04 | Private-route guard | src/app/(dashboard)/layout.tsx:15-23 | No session | Redirect with encoded current path | useSession | Login redirect; skeleton during loading. |
| T-011 | S-05 | Logo/sidebar navigation | src/app/shell.tsx:150-180 | Click | Navigate | None | Dashboard, repositories, scans, findings, reports, or help. |
| T-012 | S-05 | Start security scan | src/app/shell.tsx:221-222 | Click | Open ScanDialog | None | Scan dialog. |
| T-013 | S-05 | Search/command | src/app/shell.tsx:308-325 | Click/keyboard/select | Open command UI and navigate | None | Matching route or settings demo. |
| T-014 | S-05 | Theme toggle | src/app/shell.tsx:341 | Click | Toggle theme | next-themes | Cosmetic light/dark change. |
| T-015 | S-05 | Notification/profile/workspace overlays | src/app/shell.tsx:160,259,389-488 | Click | Open/close overlay | None | Cosmetic overlay; contained links may navigate. |
| T-016 | S-05 | Account settings | src/app/shell.tsx:583-584 | Click | Navigate | None | Settings. |
| T-017 | S-05 | Sign out | src/app/shell.tsx:620-625 | Confirm | Logout, clear cache, navigate | useLogout | Login; failure leaves the dialog. |
| T-018 | S-06 | Return to dashboard | src/app/error.tsx:11 | Click | Navigate | None | Dashboard. |
| T-019 | S-08 | Add repository | src/app/dashboard.tsx:63,169 | Click | Navigate | None | Add repository. |
| T-020 | S-08 | Start scan | src/app/dashboard.tsx:164 | Click | Open dialog | None | ScanDialog. |
| T-021 | S-08 | Findings/scans/repository/report links | src/app/dashboard.tsx:248-426 | Click | Navigate | None | Corresponding list/detail route. |
| T-022 | S-09 | Repository search | src/app/repositories.tsx:176 | Input | Filter local results | None | Matching cards or filtered-empty state. |
| T-023 | S-09 | Repository filter | src/app/repositories.tsx:142 | Click | Filter local results | None | All/open/no-open result set. |
| T-024 | S-09 | Add repository | src/app/repositories.tsx:91,121 | Click | Navigate | None | Add repository. |
| T-025 | S-09 | Repository card | src/app/repositories.tsx:194-204 | Click | Navigate | None | Repository detail. |
| T-026 | S-09 | Start scan | src/app/repositories.tsx:204-220 | Click | Open dialog | None | ScanDialog. |
| T-027 | S-09 | Overflow menu | src/app/repositories.tsx:235-335 | Click | Open view/report/delete dialog | None | Action-specific route or mutation. |
| T-028 | S-09 | Delete repository | src/app/repositories.tsx:235-335 | Confirm | Delete and invalidate lists | useDeleteRepository | Updated list; error toast. |
| T-029 | S-10 | Repository URL input | src/app/repositories.tsx:441-496 | Type | Update form state | None | Validation becomes available. |
| T-030 | S-10 | Validate | src/app/repositories.tsx:497 | Click | Validate URL | useValidateRepository | Preview metadata; scenario/error state. |
| T-031 | S-10 | Reset validation | src/app/repositories.tsx:500 | Click | Clear preview | None | Idle form. |
| T-032 | S-10 | Permission confirmation | src/app/repositories.tsx:580-630 | Confirm | Confirm GitHub access then create | useCreateRepository | Repository detail; denied/error state. |
| T-033 | S-11 | Breadcrumb/back repository | src/app/repositories.tsx:730 | Click | Navigate | None | Repository list. |
| T-034 | S-11 | Report and scan links | src/app/repositories.tsx:759,864,957,970 | Click | Navigate | None | Report or scan detail. |
| T-035 | S-11 | Scan buttons | src/app/repositories.tsx:763,876,990,1028 | Click | Open dialog | None | ScanDialog. |
| T-036 | S-11 | GitHub link | src/app/repositories.tsx:788 | Click | External navigation | repo.url | GitHub site. |
| T-037 | S-11 | Repository tabs | src/app/repositories.tsx:845 | Click | Change tab/query | None | Overview/scans/findings/reports panel. |
| T-038 | S-11 | Finding link | src/app/repositories.tsx:1002 | Click | Navigate | None | Finding detail. |
| T-039 | S-12/S-27 | Branch selector | src/app/components.tsx:726-733 | Type/select | Set selected branch | useRepositoryBranches | Branch retained; disabled on loading/error/one-branch. |
| T-040 | S-27 | Cancel/close scan | src/app/components.tsx:833 | Click/Escape | Close dialog | None | Underlying screen; cosmetic close. |
| T-041 | S-27 | Start scan | src/app/components.tsx:849-861 | Valid repository/branch | Trigger and navigate | useTriggerScan | Scan detail; GitHub/queue error notice/toast. |
| T-042 | S-13 | Scan search | src/app/scans.tsx:103-115 | Input | Filter history | None | Matching/empty result. |
| T-043 | S-13 | Status/date/repository filters | src/app/scans.tsx:116-150 | Select | Filter history | None | Filtered history. |
| T-044 | S-13 | Scan/detail/finding/report links | src/app/scans.tsx:157,204,213,231 | Click | Navigate | None | Scan, findings, or report route. |
| T-045 | S-14 | Scan tabs | src/app/scans.tsx:748 | Click | Change tab/query | None | Overview/findings/scanners/history. |
| T-046 | S-14 | View findings | src/app/scans.tsx:458,497,727 | Click | Navigate | None | Scan findings. |
| T-047 | S-14/S-20 | Download PDF | src/app/scans.tsx:483; src/app/reports.tsx:325 | Click | Generate/download blob | useGenerateReport/useDownloadReportPdf | File download and success toast; error toast. |
| T-048 | S-14 | Rescan/retry | src/app/scans.tsx:445,637,662,691,992 | Click | Open scan dialog with prior branch | None | User chooses branch and starts new scan. |
| T-049 | S-14 | Cancel scan | src/app/scans.tsx:681-687 | Click | Disabled/no-op | None | Cosmetic unsupported notice. |
| T-050 | S-14 | Scan polling | src/lib/api/hooks.ts:195-211 | Query interval | Refetch status | useScanStatus | Stops at terminal status; progress updates. |
| T-051 | S-15 | Findings filters/search/sort/page | src/app/findings.tsx:233-433 | Input/select/button | Filter/sort/paginate | None | Updated list or empty state. |
| T-052 | S-15 | Finding links | src/app/findings.tsx:287,322,363 | Click | Navigate | None | Finding detail. |
| T-053 | S-15 | Filters drawer | src/app/findings.tsx:233,525-528 | Click | Open/apply/clear/close | None | List changes or cosmetic close. |
| T-054 | S-15 | Parent links | src/app/findings.tsx:352,403,571 | Click | Navigate | None | Repository, repositories, or scans. |
| T-055 | S-16 | Detail section/context controls | src/app/findings.tsx:670,792,848 | Click | Scroll/change context | None | Cosmetic page-content change. |
| T-056 | S-16 | Finding status dialog | src/app/findings.tsx:1105,1130,1170 | Click | Open/close | None | Triage dialog. |
| T-057 | S-16 | Save finding status | src/app/findings.tsx:1190-1225 | Submit | Update finding | useUpdateFinding | Invalidate detail/list/dashboard; toast success/error. |
| T-058 | S-19 | Report search/filter | src/app/reports.tsx:90-100 | Input/select | Filter report list | None | Matching/empty list. |
| T-059 | S-19 | Report view/download | src/app/reports.tsx:100,123,149 | Click | Navigate or download | Report hooks | Detail/PDF/toast or error. |
| T-060 | S-20 | View scan | src/app/reports.tsx:217,286 | Click | Navigate | None | Scan detail. |
| T-061 | S-20 | Retry generation | src/app/reports.tsx:220,250 | Click | Reset demo generation state | Local state | Generating/ready preview; current handler has no generation API call. |
| T-062 | S-21 | Save profile | src/app/settings.tsx:182-255 | Submit | Update profile | useUpdateProfile | Session refresh; toast success/error. |
| T-063 | S-21 | Password change | src/app/settings.tsx:295,615-670 | Open/submit | Update password | useUpdatePassword | Success/validation/error. |
| T-064 | S-21 | Sign out | src/app/settings.tsx:275,670-707 | Confirm | Logout/cache clear/navigate | useLogout | Login. |
| T-065 | S-22 | Permissions | src/app/settings.tsx:351 | Click | Open/close dialog | None | Cosmetic unless permission content is expanded. |
| T-066 | S-22 | GitHub connect/disconnect | src/app/settings.tsx:365-385 | Click | Integration mutation | useGitHubConnect/useGitHubDisconnect | Query invalidation and success/error toast. |
| T-067 | S-23 | Notification switch | src/app/settings.tsx:425-440 | Toggle | Update account settings | useUpdateSettings | Persisted preference and toast; error retains prior state. |
| T-068 | S-24 | Role selector | src/app/settings.tsx:470-485 | Select | Update demo role | useSetRole/local state | Users tab visibility changes. |
| T-069 | S-25 | Repository access switch | src/app/settings.tsx:520-548 | Toggle | Update access | useSetRepositoryAccess | Repository query invalidated; visibility changes. |
| T-070 | S-25 | State explorer | src/app/settings.tsx:565 | Click | Navigate with state query | None | Loading/empty/error/unauthorized preview. |
| T-071 | S-25 | Reset demo | src/app/settings.tsx:582,703-735 | Confirm | Reset mock data/cache | useResetDemo | Reset toast; failure leaves dialog. |
| T-072 | S-26 | Repository/help CTA | src/app/settings.tsx:808 and help page | Click | Navigate | None | Add repository. |
| T-073 | All | Browser back/forward | Browser history | Browser action | Restore prior route/query | Next router | Route re-renders; no custom handler. |
| T-074 | All | Keyboard controls | Base UI dialog/select/input primitives | Enter/Escape/tab | Invoke equivalent submit/select/close | Depends on control | Same result as pointer action. |

Cosmetic controls: password reveal, theme toggle, overlay open/close, section jumps, context carousel, disabled scan cancel, and dialog close.
