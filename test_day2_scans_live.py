import httpx
import uuid
import time

BASE_URL = "http://127.0.0.1:8000/api"

def print_test(name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name} {f'({detail})' if detail else ''}")

def run_day2_tests():
    print("\n" + "="*65)
    print(" 🧪 REPO SECURITY AUDITOR — DAY 2 SCAN ENGINE VERIFICATION")
    print("="*65 + "\n")

    client = httpx.Client(base_url=BASE_URL, timeout=45.0)

    # 1. Setup User A
    user_a_email = f"scanner_a_{uuid.uuid4().hex[:6]}@example.com"
    password = "SecurePassword123!"

    reg_res = client.post("/auth/register", json={"name": "Scanner Tester", "email": user_a_email, "password": password})
    token_a = reg_res.json().get("data", {}).get("token")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Add a test repository (using small public repo for fast testing)
    test_repo_url = "https://github.com/octocat/Hello-World"
    repo_res = client.post("/repositories", headers=headers_a, json={"url": test_repo_url})
    if repo_res.status_code != 201:
        # If already added, fetch existing
        list_res = client.get("/repositories", headers=headers_a)
        repo_id = list_res.json()["data"][0]["id"]
    else:
        repo_id = repo_res.json()["data"]["id"]

    print(f"Target Test Repository ID: {repo_id} ({test_repo_url})\n")

    # -------------------------------------------------------------
    # TEST 1: Dispatch Scan (POST /api/scans)
    # -------------------------------------------------------------
    scan_res = client.post("/scans", headers=headers_a, json={"repositoryId": repo_id, "branch": "master"})
    passed = scan_res.status_code == 201 and scan_res.json().get("data", {}).get("status") == "queued"
    scan_id = scan_res.json().get("data", {}).get("id")
    print_test("1. Dispatch Scan Job (POST /scans)", passed, f"Status: queued, Scan ID: {scan_id}")

    # -------------------------------------------------------------
    # TEST 2: Poll Progress (GET /api/scans/{id}/status)
    # -------------------------------------------------------------
    print("\nPolling scan progress from background execution...")
    completed = False
    for attempt in range(15):
        time.sleep(1.5)
        status_res = client.get(f"/scans/{scan_id}/status", headers=headers_a)
        if status_res.status_code == 200:
            status_data = status_res.json().get("data", {})
            curr_status = status_data.get("status")
            progress = status_data.get("progress")
            print(f"   -> Progress: {progress}% (Status: {curr_status})")
            if curr_status in ("completed", "failed"):
                completed = curr_status == "completed"
                break

    print_test("2. Background Execution & Progress Polling (GET /scans/{id}/status)", completed, f"Final Status: {curr_status}")

    # -------------------------------------------------------------
    # TEST 3: Retrieve Completed Scan Summary (GET /api/scans/{id})
    # -------------------------------------------------------------
    detail_res = client.get(f"/scans/{scan_id}", headers=headers_a)
    passed = detail_res.status_code == 200 and detail_res.json().get("data", {}).get("progress") == 100
    findings_count = detail_res.json().get("data", {}).get("findingsCount", {})
    print_test("3. Retrieve Completed Scan Details (GET /scans/{id})", passed, f"Findings Summary: {findings_count}")

    # -------------------------------------------------------------
    # TEST 4: Query Scan Findings (GET /api/scans/{id}/findings)
    # -------------------------------------------------------------
    findings_res = client.get(f"/scans/{scan_id}/findings", headers=headers_a)
    passed = findings_res.status_code == 200 and "pagination" in findings_res.json()
    findings_list = findings_res.json().get("data", [])
    print_test("4. Query Normalized Scan Findings (GET /scans/{id}/findings)", passed, f"Findings Stored: {len(findings_list)}")

    # -------------------------------------------------------------
    # TEST 5: Test In-Flight Cancellation (POST /api/scans/{id}/cancel)
    # -------------------------------------------------------------
    # Start a 2nd scan to test cancellation
    scan2_res = client.post("/scans", headers=headers_a, json={"repositoryId": repo_id, "branch": "master"})
    scan2_id = scan2_res.json()["data"]["id"]

    cancel_res = client.post(f"/scans/{scan2_id}/cancel", headers=headers_a)
    passed = cancel_res.status_code == 200 and cancel_res.json().get("data", {}).get("status") == "cancelled"
    print_test("5. In-Flight Scan Cancellation (POST /scans/{id}/cancel)", passed, f"Status: cancelled")

    # -------------------------------------------------------------
    # TEST 6: Reject Cancellation on Completed Scan (422 Unprocessable)
    # -------------------------------------------------------------
    invalid_cancel_res = client.post(f"/scans/{scan_id}/cancel", headers=headers_a)
    passed = invalid_cancel_res.status_code == 422
    print_test("6. Reject Cancelling Completed Scan (422 Unprocessable)", passed, f"Status: {invalid_cancel_res.status_code}")

    # -------------------------------------------------------------
    # TEST 7: Access Control & IDOR Protection on Scans (FR-10)
    # -------------------------------------------------------------
    user_b_email = f"attacker_b_{uuid.uuid4().hex[:6]}@example.com"
    token_b = client.post("/auth/register", json={"name": "Attacker", "email": user_b_email, "password": password}).json()["data"]["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    idor_res = client.get(f"/scans/{scan_id}", headers=headers_b)
    passed = idor_res.status_code == 404
    print_test("7. Prevent User B from reading User A's Scan (IDOR Defense)", passed, f"Status: {idor_res.status_code}")

    # -------------------------------------------------------------
    # TEST 8: Scan History List with Pagination (GET /api/scans)
    # -------------------------------------------------------------
    history_res = client.get("/scans", headers=headers_a)
    passed = history_res.status_code == 200 and len(history_res.json().get("data", [])) >= 2
    print_test("8. Scan History List (GET /scans)", passed, f"Total Scans in History: {len(history_res.json().get('data', []))}")

    print("\n" + "="*65)
    print(" 🏁 ALL DAY 2 SCANNER & ORCHESTRATOR TESTS COMPLETED!")
    print("="*65 + "\n")

if __name__ == "__main__":
    run_day2_tests()