# Link and Action Inventory

| File:Line | Type | Handler | Classification |
|---|---|---|---|
| app/auth.tsx:88 | onClick | `() => signIn(true)`... | Works UI-only |
| app/auth.tsx:130 | onClick | `() => setForgot(true)`... | Works UI-only |
| app/auth.tsx:152 | onClick | `() => setShow((current) => !current)`... | Works UI-only |
| app/auth.tsx:204 | onClick | `() => signIn(true)`... | Works UI-only |
| app/components.tsx:117 | to | `to`... | Works UI-only |
| app/components.tsx:417 | to | `"/dashboard">Back to dashboard</LinkButt`... | Works UI-only |
| app/components.tsx:441 | onClick | `() => setParams({`... | Works UI-only |
| app/components.tsx:452 | to | `"/dashboard">Back to dashboard</LinkButt`... | Works UI-only |
| app/components.tsx:462 | onClick | `() => setParams({`... | Works UI-only |
| app/components.tsx:470 | to | `"/dashboard">Back to dashboard</LinkButt`... | Works UI-only |
| app/components.tsx:480 | to | `"/repositories/new" variant="default">`... | Works UI-only |
| app/components.tsx:623 | to | ``/repositories/${repo.id`... | Works UI-only |
| app/components.tsx:658 | to | ``/repositories/${repo.id`... | Works UI-only |
| app/components.tsx:699 | to | ``/repositories/${repo.id`... | Works UI-only |
| app/components.tsx:822 | to | `"/settings?tab=github">`... | Works UI-only |
| app/components.tsx:833 | onClick | `() => onOpenChange(false)`... | Works UI-only |
| app/components.tsx:925 | onClick | `() => setOpen(true)`... | Works UI-only |
| app/components.tsx:946 | onClick | `() => setOpen(false)`... | Works UI-only |
| app/components.tsx:949 | onClick | `download`... | Works UI-only |
| app/components.tsx:973 | to | `item.to`... | Works UI-only |
| app/dashboard.tsx:63 | to | `"/repositories/new" variant="default">`... | Works UI-only |
| app/dashboard.tsx:164 | onClick | `() => setScanOpen(true)`... | Works UI-only |
| app/dashboard.tsx:169 | to | `"/repositories/new" variant="default">`... | Works UI-only |
| app/dashboard.tsx:248 | to | `"/findings"`... | Works UI-only |
| app/dashboard.tsx:261 | to | `"/scans"`... | Works UI-only |
| app/dashboard.tsx:272 | to | ``/scans/${scan.id`... | Works UI-only |
| app/dashboard.tsx:312 | to | `"/findings" variant="ghost" className="h`... | Works UI-only |
| app/dashboard.tsx:345 | to | ``/scans/${scan?.id || "12"`... | Works UI-only |
| app/dashboard.tsx:375 | to | ``/scans/${scan?.id || "12"`... | Works UI-only |
| app/dashboard.tsx:397 | to | ``/scans/${scan?.id`... | Works UI-only |
| app/dashboard.tsx:426 | to | `"/repositories"`... | Works UI-only |
| app/error.tsx:11 | to | `"/dashboard">Return to dashboard</LinkBu`... | Works UI-only |
| app/findings.tsx:233 | onClick | `() => setFiltersOpen(true)`... | Works UI-only |
| app/findings.tsx:244 | onClick | `clear`... | Works UI-only |
| app/findings.tsx:287 | to | `findingPath(findingRecord)`... | Works UI-only |
| app/findings.tsx:322 | to | `findingPath(findingRecord)`... | Works UI-only |
| app/findings.tsx:347 | onClick | `clear`... | Works UI-only |
| app/findings.tsx:352 | to | `scanId === "all" ? "/repositories" : `/r`... | Works UI-only |
| app/findings.tsx:363 | to | `findingPath(findingRecord)`... | Works UI-only |
| app/findings.tsx:401 | onClick | `clear`... | Works UI-only |
| app/findings.tsx:403 | to | `"/repositories">View repositories</LinkB`... | Works UI-only |
| app/findings.tsx:421 | onClick | `() => setPage((current) => current - 1)`... | Works UI-only |
| app/findings.tsx:433 | onClick | `() => setPage((current) => current + 1)`... | Works UI-only |
| app/findings.tsx:525 | onClick | `clear`... | Works UI-only |
| app/findings.tsx:528 | onClick | `() => setFiltersOpen(false)`... | Works UI-only |
| app/findings.tsx:571 | to | `"/scans">Back to scans</LinkButton>`... | Works UI-only |
| app/findings.tsx:640 | to | ``/reports/${scan.id`... | Works UI-only |
| app/findings.tsx:670 | onClick | `() => jump(section)`... | Works UI-only |
| app/findings.tsx:792 | onClick | `() => setContextIndex(index)`... | Works UI-only |
| app/findings.tsx:848 | onClick | `() => jump("evidence")`... | Works UI-only |
| app/findings.tsx:1105 | to | ``/scans/${scan.id`... | Works UI-only |
| app/findings.tsx:1169 | onClick | `() => setStatusOpen(false)`... | Works UI-only |
| app/reports.tsx:100 | to | ``/reports/${scan.id`... | Works UI-only |
| app/reports.tsx:123 | to | ``/reports/${scan.id`... | Works UI-only |
| app/reports.tsx:152 | to | `"/repositories">`... | Works UI-only |
| app/reports.tsx:196 | to | `"/reports">View reports</LinkButton>`... | Works UI-only |
| app/reports.tsx:217 | to | ``/scans/${scan.id`... | Works UI-only |
| app/reports.tsx:220 | onClick | `retry`... | Works UI-only |
| app/reports.tsx:248 | to | ``/scans/${scan.id`... | Works UI-only |
| app/reports.tsx:250 | onClick | `() => setParams({`... | Works UI-only |
| app/reports.tsx:263 | to | ``/repositories/${repo.id`... | Works UI-only |
| app/reports.tsx:286 | to | ``/scans/${scan.id`... | Works UI-only |
| app/reports.tsx:376 | to | ``/scans/${scan.id`... | Works UI-only |
| app/reports.tsx:401 | to | ``/scans/${scan.id`... | Works UI-only |
| app/reports.tsx:421 | to | ``/scans/${scan.id`... | Works UI-only |
| app/reports.tsx:453 | to | ``/scans/${scan.id`... | Works UI-only |
| app/reports.tsx:483 | to | ``/scans/${scan.id`... | Works UI-only |
| app/repositories.tsx:91 | to | `"/repositories/new" variant="default">`... | Works UI-only |
| app/repositories.tsx:121 | to | `"/repositories/new" variant="default">`... | Works UI-only |
| app/repositories.tsx:142 | onClick | `() => setFilter(item)`... | Works UI-only |
| app/repositories.tsx:235 | onClick | `() => setMore(repo)`... | Works UI-only |
| app/repositories.tsx:312 | to | ``/repositories/${more?.id`... | Works UI-only |
| app/repositories.tsx:322 | to | ``/reports/${scans.find((scanRecord) => s`... | Works UI-only |
| app/repositories.tsx:497 | onClick | `validate`... | Works UI-only |
| app/repositories.tsx:500 | onClick | `() => setState("idle")`... | Works UI-only |
| app/repositories.tsx:610 | onClick | `() => setGithub(true)`... | Works UI-only |
| app/repositories.tsx:730 | to | `"/repositories">View repositories</LinkB`... | Works UI-only |
| app/repositories.tsx:759 | onClick | `() => report && navigate(`/reports/${rep`... | Works UI-only |
| app/repositories.tsx:763 | onClick | `() => setScanOpen(true)`... | Works UI-only |
| app/repositories.tsx:788 | href | `repo.url || `https://github.com/${repo.n`... | Works UI-only |
| app/repositories.tsx:864 | to | ``/scans/${latest.id`... | Works UI-only |
| app/repositories.tsx:876 | onClick | `() => setScanOpen(true)`... | Works UI-only |
| app/repositories.tsx:957 | to | ``/scans/${scan.id`... | Works UI-only |
| app/repositories.tsx:970 | to | ``/scans/${scan.id`... | Works UI-only |
| app/repositories.tsx:990 | onClick | `() => setScanOpen(true)`... | Works UI-only |
| app/repositories.tsx:1002 | to | ``/scans/${finding.scanId || report?.id |`... | Works UI-only |
| app/repositories.tsx:1028 | onClick | `() => setScanOpen(true)`... | Works UI-only |
| app/repositories.tsx:1057 | to | ``/reports/${scan.id`... | Works UI-only |
| app/scans.tsx:90 | onClick | `() => setScanOpen(true)`... | Works UI-only |
| app/scans.tsx:157 | to | ``/scans/${scan.id`... | Works UI-only |
| app/scans.tsx:204 | to | ``/scans/${scan.id`... | Works UI-only |
| app/scans.tsx:213 | to | ``/reports/${scan.id`... | Works UI-only |
| app/scans.tsx:280 | to | ``/scans/${scan.id`... | Works UI-only |
| app/scans.tsx:294 | to | ``/scans/${scan.id`... | Works UI-only |
| app/scans.tsx:340 | to | `"/scans">View scan history</LinkButton>`... | Works UI-only |
| app/scans.tsx:386 | to | ``/scans/${scan.retryOf`... | Works UI-only |
| app/scans.tsx:445 | onClick | `() => setScanOpen(true)`... | Works UI-only |
| app/scans.tsx:458 | to | ``/scans/${scan.id`... | Works UI-only |
| app/scans.tsx:637 | onClick | `retry`... | Works UI-only |
| app/scans.tsx:662 | onClick | `retry`... | Works UI-only |
| app/scans.tsx:666 | to | ``/repositories/${repo.id`... | Works UI-only |
| app/scans.tsx:688 | to | ``/scans/${scan.id`... | Works UI-only |
| app/scans.tsx:691 | onClick | `retry`... | Works UI-only |
| app/scans.tsx:789 | to | ``/scans/${scan.id`... | Works UI-only |
| app/scans.tsx:904 | to | `item.to`... | Works UI-only |
| app/scans.tsx:992 | onClick | `retry`... | Works UI-only |
| app/scans.tsx:998 | to | ``/scans/${scan.id`... | Works UI-only |
| app/scans.tsx:1020 | to | ``/scans/${item.id`... | Works UI-only |
| app/settings.tsx:275 | onClick | `() => setSignout(true)`... | Works UI-only |
| app/settings.tsx:295 | onClick | `() => setPasswordOpen(true)`... | Works UI-only |
| app/settings.tsx:351 | onClick | `() => setPermissions(true)`... | Works UI-only |
| app/settings.tsx:544 | to | `"/repositories/web-app">`... | Works UI-only |
| app/settings.tsx:547 | to | `"/scans/12">Test scan access</LinkButton`... | Works UI-only |
| app/settings.tsx:548 | to | `"/reports/12">Test report access</LinkBu`... | Works UI-only |
| app/settings.tsx:565 | to | ``${example.path`... | Works UI-only |
| app/settings.tsx:582 | onClick | `() => setReset(true)`... | Works UI-only |
| app/settings.tsx:601 | to | `"/settings">Back to profile</LinkButton>`... | Works UI-only |
| app/settings.tsx:703 | onClick | `() => setSignout(false)`... | Works UI-only |
| app/settings.tsx:727 | onClick | `() => setReset(false)`... | Works UI-only |
| app/settings.tsx:808 | to | `"/repositories/new" variant="default">`... | Works UI-only |
| app/shell.tsx:117 | to | ``/login?redirect=${encodeURIComponent(lo`... | Works UI-only |
| app/shell.tsx:150 | to | `"/dashboard"`... | Works UI-only |
| app/shell.tsx:160 | onClick | `() => setWorkspace(true)`... | Works UI-only |
| app/shell.tsx:176 | to | `item.path`... | Works UI-only |
| app/shell.tsx:198 | to | `"/settings"`... | Works UI-only |
| app/shell.tsx:221 | to | `"/repositories/new"`... | Works UI-only |
| app/shell.tsx:222 | onClick | `() => setMobile(false)`... | Works UI-only |
| app/shell.tsx:247 | to | `"/help"`... | Works UI-only |
| app/shell.tsx:259 | onClick | `() => setProfile(true)`... | Works UI-only |
| app/shell.tsx:294 | onClick | `() => setMobile(true)`... | Works UI-only |
| app/shell.tsx:308 | onClick | `() => setCommand(true)`... | Works UI-only |
| app/shell.tsx:321 | onClick | `() => setCommand(true)`... | Works UI-only |
| app/shell.tsx:325 | to | `"/settings?tab=demo">`... | Works UI-only |
| app/shell.tsx:341 | onClick | `() => setTheme(isDark ? "light" : "dark"`... | Works UI-only |
| app/shell.tsx:389 | to | ``/scans/${securityAlert.scanId`... | Works UI-only |
| app/shell.tsx:390 | onClick | `() => setNotifications(false)`... | Works UI-only |
| app/shell.tsx:430 | to | ``/scans/${scan.id`... | Works UI-only |
| app/shell.tsx:431 | onClick | `() => setNotifications(false)`... | Works UI-only |
| app/shell.tsx:474 | onClick | `() => setUnread(false)`... | Works UI-only |
| app/shell.tsx:488 | onClick | `() => setProfile(true)`... | Works UI-only |
| app/shell.tsx:583 | to | `"/settings"`... | Works UI-only |
| app/shell.tsx:584 | onClick | `() => setProfile(false)`... | Works UI-only |
| app/shell.tsx:615 | to | `"/settings?tab=demo">`... | Works UI-only |
