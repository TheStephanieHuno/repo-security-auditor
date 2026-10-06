# Security Test Plan and Findings Validation

**Tickets:** RSA-70 (O-14, O-15), RSA-93 (O-16)
**SRS:** FR-04, FR-06, FR-10, NFR-01, NFR-03
**Owner:** Joseph · **Last executed:** 2026-10-06

This plan has two parts: (A) validation that each scanner category reports
real issues at the correct severity, and (B) security test cases for the API.
Every case is automated; the "Test" column names the pytest function.

## How to run

```bash
pip install -r requirements-dev.txt
pytest                                   # full suite, in-process

# Real scanner binaries (otherwise those cases are skipped)
GITLEAKS_PATH=/path/to/gitleaks SEMGREP_PATH=/path/to/semgrep pytest tests/test_scanners.py tests/test_scanner_rules.py

# Security suite against a running server (O-16)
uvicorn app.main:app --port 8765 &
RSA_LIVE_BASE_URL=http://127.0.0.1:8765 pytest tests/test_api_security.py
```

## A. Findings validation by scan category (O-14)

Severity expectations are fixed in `tests/test_scanner_rules.py`. The
recorded outputs in `tests/fixtures/scanner_outputs/` were produced by
gitleaks 8.30.1 and semgrep 1.179.0 running the project rules on a sample
repository, so these tests check real scanner output, not hand-written JSON.

### Secrets (Gitleaks, `app/scanners/rules/gitleaks.toml`)

| ID | Case | Expected | Test |
|---|---|---|---|
| SEC-01 | AWS access key ID / secret access key | CRITICAL | `test_gitleaks_rule_matches_positives_and_rejects_negatives` |
| SEC-02 | GitHub classic and fine-grained tokens | CRITICAL | same |
| SEC-03 | Private key block | CRITICAL | same |
| SEC-04 | Database URL or `DB_PASSWORD` assignment | HIGH | same |
| SEC-05 | Placeholders (`${VAR}`, `<password>`, `changeme`) | not reported | same (negative samples) |
| SEC-06 | Upstream rules overlapping project rules | disabled, one finding per secret | `test_gitleaks_config_extends_defaults_without_duplicates` |
| SEC-07 | Secret value never stored in Finding/Evidence | masked (`ghp_********` / `REDACTED`) | `test_gitleaks_normalization_masks_secrets`, `test_recorded_gitleaks_output_maps_to_expected_severities` |

### Code patterns (Semgrep, `app/scanners/rules/semgrep/`)

| ID | Case | Expected | Test |
|---|---|---|---|
| CODE-01 | eval/exec, shell=True, string-built SQL (Python, JS) | HIGH | `test_recorded_semgrep_output_maps_to_expected_severities` |
| CODE-02 | os.system, pickle, unsafe YAML, disabled TLS, DOM XSS sinks, `new Function` | MEDIUM | same |
| CODE-03 | Safe variants (literals, parameterized SQL, `yaml.safe_load`) | not reported | `test_semgrep_rule_unit_tests_pass` (`ok:` annotations) |
| CODE-04 | `# nosemgrep` in scanned code | ignored (`--disable-nosem`) | `test_wrapper_commands_are_hardened` |
| CODE-05 | Snippet evidence present despite "requires login" | real source line | `test_semgrep_normalization_rule_ids_and_snippets`, `test_real_semgrep_scan` |

### Dependencies (OSV API)

| ID | Case | Expected | Test |
|---|---|---|---|
| DEP-01 | GHSA severity label (LOW/MODERATE/HIGH/CRITICAL) | mapped (MODERATE→MEDIUM) | `test_osv_normalization_deduplicates_aliases_and_recommends_fix` |
| DEP-02 | CVSS v3 vector only | computed base score → band | `test_cvss_base_scores_match_reference_values` |
| DEP-03 | Same advisory under GHSA/PYSEC/CVE IDs | one finding | `test_osv_normalization_deduplicates_aliases_and_recommends_fix` |
| DEP-04 | Range spec (`^1.2.3`) | confidence lowered | same |
| DEP-05 | Unsafe vulnerability ID from API | never used in a URL | `test_osv_check_queries_api_and_ignores_unsafe_ids` |
| DEP-06 | OSV outage | scanner FAILED, others unaffected | `test_osv_outage_fails_the_check` |

### Insecure configuration

| ID | Case | Expected | Test |
|---|---|---|---|
| CFG-01 | Committed `.env` with credentials | HIGH, variable names only as evidence | `test_config_checks_detect_env_debug_and_cors` |
| CFG-02 | Flask `debug=True` | HIGH | same |
| CFG-03 | Django `DEBUG = True`, debug flags in config files | MEDIUM | same |
| CFG-04 | CORS wildcard / allow-all | MEDIUM, HIGH with credentials | same |
| CFG-05 | `.env.example`, explicit origin allowlists, `node_modules` | not reported | same, `test_config_checks_skip_vendor_dirs_and_symlinks` |

### Live validation (2026-10-06)

A full scan of `github.com/OWASP/NodeGoat` through the running API reported 24
findings (2 critical, 14 high, 6 medium, 2 low) across all four scanners,
including the known server-side JavaScript injection
(`eval(req.body.preTax)` in `app/routes/contributions.js`, HIGH), the
committed TLS private key (CRITICAL), and vulnerable `underscore 1.8.3`
(CRITICAL). The generated PDF report rendered 10 pages.

## B. API security test cases (O-15, executed under O-16)

| ID | Threat | Case | Expected | Test |
|---|---|---|---|---|
| API-01 | Broken authentication | Every non-public endpoint (enumerated from OpenAPI) without a token | 401 + `WWW-Authenticate` | `test_every_protected_endpoint_requires_authentication` |
| API-02 | Token forgery | garbage, `alg: none`, wrong key, expired, wrong scheme | 401 | `test_forged_expired_and_revoked_tokens_are_rejected` |
| API-03 | Session persistence | Token used after logout | 401 | same, `test_logout_revokes_the_token` |
| API-04 | Credential stuffing | 5 failed logins for one email/IP | 429 | `test_repeated_login_failures_are_rate_limited` |
| API-05 | Account enumeration | Login and password-reset responses for unknown vs known email | identical | `test_login_success_and_uniform_failure_message`, `test_password_reset_does_not_reveal_accounts` |
| API-06 | IDOR / FR-10 | User B reads, deletes, cancels, scans, or reports on user A's resources | 404, A's data unchanged | `test_users_cannot_read_or_change_each_others_resources` |
| API-07 | Mass assignment | `role: administrator` in registration | ignored | `test_registration_ignores_privilege_fields` |
| API-08 | Malformed input | invalid JSON, wrong types, unknown enums | 422 envelope, input not echoed | `test_malformed_bodies_return_validation_errors` |
| API-09 | Injection | SQL/path-traversal strings in query and path parameters | 404/422, no 500, no internals | `test_injection_style_parameters_are_rejected_safely` |
| API-10 | SSRF | metadata IP, `github.com@evil`, `file://`, SSH URLs | 422 | `test_repository_urls_cannot_target_other_hosts` |
| API-11 | Command injection via git | branch `--upload-pack=…`, `;`, `..` | 422, nothing dispatched | `test_start_scan_rejects_unsafe_branch_names` |
| API-12 | Information leakage | Any error body | no stack traces, SQL, or paths | `assert_error_envelope` in every security test |
| API-13 | Secret exposure | Password hashes in responses | never present | `test_responses_never_expose_password_hashes` |
| API-14 | Browser hardening | nosniff, frame-deny, no-store; CORS for unlisted origin | headers set; origin not allowed | `test_security_headers_and_cors_policy` |
| API-15 | Prompt injection | Repository text containing instructions sent to the LLM | wrapped as untrusted data; secrets redacted | `test_explanation_is_grounded_and_persisted` |
| API-16 | PDF markup injection | `<script>`, unclosed tags, `&` in finding text | escaped, PDF renders | `test_pdf_renders_with_markup_like_content` |
| API-17 | Untrusted repository content | Symlinks to host files, paths outside workspace | not followed / rejected | `test_relative_paths_cannot_escape_workspace`, `test_config_checks_skip_vendor_dirs_and_symlinks` |

## Results

| Run | Command | Result |
|---|---|---|
| Full suite, in-process | `pytest` | 150 passed, 3 skipped (real-binary cases) |
| Real binaries | `GITLEAKS_PATH=… SEMGREP_PATH=… pytest -k real` + `semgrep --test` | passed (13/13 Semgrep rule tests) |
| Live server (O-16) | `RSA_LIVE_BASE_URL=… pytest tests/test_api_security.py` | 24 passed |
| Clean install of pinned requirements | fresh venv + `pytest` | 150 passed, 3 skipped |

## Known gaps

- Login rate limiting is per process; a multi-worker deployment needs a shared (Redis) limiter.
- Scans run in-process (`InProcessScanDispatcher`) until the Celery worker lands; process restarts leave in-flight scans RUNNING and need reconciliation.
- CPU/memory limits for scanner processes are not enforced yet (wall-clock and repository-size limits are).
- Private repositories are not supported; only public GitHub repositories can be added.
