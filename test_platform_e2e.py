import sys
import httpx
import uuid
import time

BASE_URL = "http://127.0.0.1:8000/api"

RESULTS: list[tuple[str, bool]] = []

def print_test(name: str, passed: bool, detail: str = ""):
    RESULTS.append((name, passed))
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name} {f'({detail})' if detail else ''}")

def run_e2e_tests():
    print("\n" + "="*70)
    print(" 🧪 REPO SECURITY AUDITOR — POSTGRESQL 16 LIVE E2E TEST SUITE")
    print("="*70 + "\n")

    client = httpx.Client(base_url=BASE_URL, timeout=45.0)

    # 1. AUTHENTICATION
    print("--- [1] PostgreSQL Authentication & Profile ---")
    user_email = f"postgres_user_{uuid.uuid4().hex[:6]}@example.com"
    password = "SecurePassword123!"

    reg_res = client.post("/auth/register", json={"name": "Postgres Tester", "email": user_email, "password": password})
    passed = reg_res.status_code == 201 and "token" in reg_res.json().get("data", {})
    token = reg_res.json().get("data", {}).get("token")
    headers = {"Authorization": f"Bearer {token}"}
    print_test("1. User Registration in PostgreSQL", passed, f"Email: {user_email}")

    profile_res = client.get("/users/me", headers=headers)
    passed = profile_res.status_code == 200 and profile_res.json().get("data", {}).get("role") == "developer"
    print_test("2. User Profile with Role Attribute", passed, "Role: developer")

    # 2. REPOSITORY MANAGEMENT
    print("\n--- [2] Live GitHub Validation & Repository CRUD ---")
    val_res = client.post("/repositories/validate", headers=headers, json={"url": "https://github.com/octocat/Hello-World"})
    passed = val_res.status_code == 200 and val_res.json().get("data", {}).get("valid") is True
    print_test("3. Live GitHub API Validation", passed, "Repo: octocat/Hello-World")

    add_res = client.post("/repositories", headers=headers, json={"url": "https://github.com/octocat/Hello-World"})
    passed = add_res.status_code == 201
    repo_id = add_res.json().get("data", {}).get("id")
    print_test("4. Add Repository to PostgreSQL", passed, f"Repo ID: {repo_id}")

    branches_res = client.get(f"/repositories/{repo_id}/branches", headers=headers)
    passed = branches_res.status_code == 200 and len(branches_res.json().get("data", [])) >= 1
    print_test("5. Live Branch Fetching from GitHub", passed, f"Branches Found: {len(branches_res.json().get('data', []))}")

    # 3. SCAN ENGINE
    print("\n--- [3] Scan Engine Execution & Progress Polling ---")
    scan_res = client.post("/scans", headers=headers, json={"repositoryId": repo_id, "branch": "master"})
    passed = scan_res.status_code == 201 and scan_res.json().get("data", {}).get("status") == "queued"
    scan_id = scan_res.json().get("data", {}).get("id")
    print_test("6. Dispatch Background Scan Job", passed, f"Scan ID: {scan_id}")

    # Poll until completed
    for _ in range(15):
        time.sleep(1.5)
        st_res = client.get(f"/scans/{scan_id}/status", headers=headers)
        if st_res.status_code == 200 and st_res.json().get("data", {}).get("status") == "completed":
            break

    status_final = client.get(f"/scans/{scan_id}", headers=headers)
    passed = status_final.status_code == 200 and status_final.json().get("data", {}).get("status") == "completed"
    print_test("7. Background Scan Execution to 100%", passed, "Status: completed")

    # 4. FINDINGS WORKSPACE
    print("\n--- [4] Findings Workspace & Review Triage ---")
    findings_res = client.get(f"/findings?repositoryId={repo_id}", headers=headers)
    passed = findings_res.status_code == 200 and "pagination" in findings_res.json()
    findings = findings_res.json().get("data", [])
    print_test("8. Workspace Findings Query with Filters", passed, f"Total Findings: {len(findings)}")

    if findings:
        target_finding = findings[0]
        finding_id = target_finding["id"]
        review_res = client.patch(
            f"/findings/{finding_id}",
            headers=headers,
            json={"reviewStatus": "acknowledged", "reviewNote": "Reviewed and verified in PostgreSQL test run."}
        )
        passed = review_res.status_code == 200 and review_res.json().get("data", {}).get("reviewStatus") == "acknowledged"
        print_test("9. Finding Triage Review (PATCH /findings/{id})", passed, "Status: acknowledged")

    # 5. PDF REPORTS
    print("\n--- [5] PDF Report Generation & Binary Streaming ---")
    gen_res = client.post("/reports", headers=headers, json={"scanId": scan_id})
    passed = gen_res.status_code == 201 and gen_res.json().get("data", {}).get("status") in ("generating", "ready")
    report_id = gen_res.json().get("data", {}).get("id")
    print_test("10. Trigger Async PDF Report Generation", passed, f"Report ID: {report_id}")

    # Wait for PDF assembly
    for _ in range(10):
        time.sleep(1.0)
        rep_status = client.get(f"/reports/{report_id}", headers=headers)
        if rep_status.status_code == 200 and rep_status.json().get("data", {}).get("status") == "ready":
            break

    rep_final = client.get(f"/reports/{report_id}", headers=headers)
    passed = rep_final.status_code == 200 and rep_final.json().get("data", {}).get("status") == "ready"
    print_test("11. Report Assembly Status (Ready)", passed, f"File Size: {rep_final.json().get('data', {}).get('fileSize')} bytes")

    # Download PDF Binary Stream
    pdf_res = client.get(f"/reports/{report_id}/pdf", headers=headers)
    passed = pdf_res.status_code == 200 and pdf_res.headers.get("content-type") == "application/pdf" and len(pdf_res.content) > 100
    print_test("12. Stream Binary PDF from PostgreSQL Metadata", passed, f"Downloaded {len(pdf_res.content)} bytes")

    # 6. DASHBOARD METRICS
    print("\n--- [6] Dashboard Metrics Aggregation ---")
    dash_res = client.get("/dashboard/metrics", headers=headers)
    passed = dash_res.status_code == 200 and dash_res.json().get("data", {}).get("repositories", {}).get("total") >= 1
    metrics = dash_res.json().get("data", {})
    print_test("13. Dashboard Metrics Aggregation from PostgreSQL", passed, f"Repos: {metrics.get('repositories')}, Scans: {metrics.get('scans', {}).get('total')}")

    failed = [name for name, ok in RESULTS if not ok]
    print("\n" + "="*70)
    if failed:
        print(f" ❌ {len(failed)} OF {len(RESULTS)} LIVE E2E CHECKS FAILED:")
        for name in failed:
            print(f"    - {name}")
    else:
        print(f" 🏁 ALL {len(RESULTS)} POSTGRESQL LIVE E2E CHECKS PASSED")
    print("="*70 + "\n")
    return not failed

if __name__ == "__main__":
    sys.exit(0 if run_e2e_tests() else 1)