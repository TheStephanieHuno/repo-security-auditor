import httpx
import uuid

BASE_URL = "http://127.0.0.1:8000/api"

def print_test(name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name} {f'({detail})' if detail else ''}")

def run_all_tests():
    print("\n" + "="*60)
    print(" 🧪 REPO SECURITY AUDITOR — DAY 1 & 2 VERIFICATION SUITE")
    print("="*60 + "\n")

    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # Unique emails for clean test run
    user_a_email = f"test_a_{uuid.uuid4().hex[:6]}@example.com"
    user_b_email = f"test_b_{uuid.uuid4().hex[:6]}@example.com"
    password = "SecurePassword123!"

    # -------------------------------------------------------------
    # 1. AUTHENTICATION & PROFILE TESTS
    # -------------------------------------------------------------
    print("--- [1] Authentication & Profile ---")

    # Test 1: Register User A
    res = client.post("/auth/register", json={"name": "Alice Tester", "email": user_a_email, "password": password})
    passed = res.status_code == 201 and "token" in res.json().get("data", {})
    token_a = res.json().get("data", {}).get("token", "")
    print_test("1. User A Registration (POST /auth/register)", passed, f"Status: {res.status_code}")

    # Test 2: Prevent Duplicate Email Registration
    res = client.post("/auth/register", json={"name": "Alice Duplicate", "email": user_a_email, "password": password})
    passed = res.status_code == 409
    print_test("2. Duplicate Email Prevention (409 Conflict)", passed, f"Status: {res.status_code}")

    # Test 3: Login User A (Valid Credentials)
    res = client.post("/auth/login", json={"email": user_a_email, "password": password})
    passed = res.status_code == 200 and res.json().get("data", {}).get("user", {}).get("role") == "developer"
    print_test("3. User A Login (POST /auth/login)", passed, f"Role: developer")

    # Test 4: Login User A (Invalid Password)
    res = client.post("/auth/login", json={"email": user_a_email, "password": "WrongPassword!"})
    passed = res.status_code == 401
    print_test("4. Invalid Password Rejection (401 Unauthorized)", passed, f"Status: {res.status_code}")

    # Test 5: Read Profile (GET /users/me)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    res = client.get("/users/me", headers=headers_a)
    passed = res.status_code == 200 and res.json().get("data", {}).get("email") == user_a_email
    print_test("5. Get Profile (GET /users/me)", passed, f"Email: {user_a_email}")

    # Test 6: Update Profile (PUT /users/me)
    res = client.put("/users/me", headers=headers_a, json={"name": "Alice Updated", "email": user_a_email})
    passed = res.status_code == 200 and res.json().get("data", {}).get("name") == "Alice Updated"
    print_test("6. Update Profile (PUT /users/me)", passed, f"New Name: Alice Updated")

    # Test 7: Update Settings (PUT /users/me/settings)
    res = client.put("/users/me/settings", headers=headers_a, json={"onScanCompletion": False, "onScanFailure": True})
    passed = res.status_code == 200 and res.json().get("data", {}).get("onScanCompletion") is False
    print_test("7. Update Notification Settings (PUT /users/me/settings)", passed)

    # -------------------------------------------------------------
    # 2. GITHUB & REPOSITORY TESTS
    # -------------------------------------------------------------
    print("\n--- [2] GitHub API Integration & Repository CRUD ---")

    # Test 8: Validate Valid Public GitHub Repo
    res = client.post("/repositories/validate", headers=headers_a, json={"url": "https://github.com/fastapi/fastapi"})
    passed = res.status_code == 200 and res.json().get("data", {}).get("valid") is True
    print_test("8. Validate Live GitHub Repo (POST /repositories/validate)", passed, "Repo: fastapi/fastapi")

    # Test 9: Validate Non-Existent GitHub Repo
    res = client.post("/repositories/validate", headers=headers_a, json={"url": "https://github.com/nonexistent-org-12345/fake-repo-98765"})
    passed = res.status_code == 400
    print_test("9. Reject Fake GitHub Repo (400 Bad Request)", passed, f"Status: {res.status_code}")

    # Test 10: Validate Non-GitHub URL (SSRF Defense)
    res = client.post("/repositories/validate", headers=headers_a, json={"url": "https://gitlab.com/some/repo"})
    passed = res.status_code == 400
    print_test("10. Reject Non-GitHub URL (SSRF Defense)", passed, f"Status: {res.status_code}")

    # Test 11: Add Repository (POST /repositories)
    res = client.post("/repositories", headers=headers_a, json={"url": "https://github.com/fastapi/fastapi"})
    passed = res.status_code == 201
    repo_id = res.json().get("data", {}).get("id") if passed else None
    print_test("11. Add Repository to Database (POST /repositories)", passed, f"Repo ID: {repo_id}")

    # Test 12: List Repositories (GET /repositories)
    res = client.get("/repositories", headers=headers_a)
    passed = res.status_code == 200 and len(res.json().get("data", [])) >= 1
    print_test("12. List Owned Repositories (GET /repositories)", passed, f"Count: {len(res.json().get('data', []))}")

    # Test 13: Fetch Live Branches from GitHub
    if repo_id:
        res = client.get(f"/repositories/{repo_id}/branches", headers=headers_a)
        branches = res.json().get("data", [])
        passed = res.status_code == 200 and any(b.get("isDefault") for b in branches)
        default_branch = next((b["name"] for b in branches if b.get("isDefault")), "None")
        print_test("13. Fetch Live GitHub Branches (GET /repositories/{id}/branches)", passed, f"Default: {default_branch}, Total: {len(branches)}")

    # -------------------------------------------------------------
    # 3. ACCESS CONTROL & SECURITY (IDOR DEFENSE)
    # -------------------------------------------------------------
    print("\n--- [3] Access Control & IDOR Defense (FR-10) ---")

    # Register User B
    res_b = client.post("/auth/register", json={"name": "Bob Attacker", "email": user_b_email, "password": password})
    token_b = res_b.json().get("data", {}).get("token", "")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Test 14: User B attempts to access User A's repository
    if repo_id:
        res = client.get(f"/repositories/{repo_id}", headers=headers_b)
        passed = res.status_code == 404  # Must be 404 (or 403), never 200!
        print_test("14. Prevent User B from reading User A's Repo (IDOR Defense)", passed, f"Status: {res.status_code}")

    # Test 15: Delete Repository (DELETE /repositories/{id})
    if repo_id:
        res = client.delete(f"/repositories/{repo_id}", headers=headers_a)
        passed = res.status_code == 204
        print_test("15. Delete Repository (DELETE /repositories/{id})", passed, "204 No Content")

    print("\n" + "="*60)
    print(" 🏁 ALL 15 AUTOMATED TESTS COMPLETED!")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_all_tests()