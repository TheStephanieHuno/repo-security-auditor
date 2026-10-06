import sqlite3, sys, json, urllib.request

def post(path, data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request('http://127.0.0.1:8000' + path,
      data=json.dumps(data).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def get(path, token=None):
    headers = {}
    if token: headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request('http://127.0.0.1:8000' + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def delete(path, token=None):
    headers = {}
    if token: headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request('http://127.0.0.1:8000' + path, headers=headers, method='DELETE')
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, res.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def patch(path, data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request('http://127.0.0.1:8000' + path,
      data=json.dumps(data).encode('utf-8'), headers=headers, method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

TOKEN = None
REPO_ID = None
SCAN_ID = None
FINDING_ID = None
REPORT_ID = None

# --- Check DB tables ---
print("=== DB TABLES ===")
try:
    c = sqlite3.connect('app.db')
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Tables:", tables)
    c.close()
except Exception as e:
    print("DB Error:", e)

# --- Journey 1: Auth ---
print("\n=== JOURNEY 1: AUTH ===")
code, body = post('/api/auth/register', {'name':'Live Tester','email':'livetest@example.com','password':'Password123!'})
print(f"REGISTER {code}:", json.dumps(body)[:300])

code2, body2 = post('/api/auth/register', {'name':'Live Tester','email':'livetest@example.com','password':'Password123!'})
print(f"REGISTER DUPE {code2}:", json.dumps(body2)[:200])

code3, body3 = post('/api/auth/login', {'email':'livetest@example.com','password':'Password123!'})
print(f"LOGIN {code3}:", json.dumps(body3)[:300])
if code3 == 200 and 'data' in body3:
    TOKEN = body3['data'].get('token')
    print(f"TOKEN: {TOKEN[:30]}..." if TOKEN else "NO TOKEN")

code4, body4 = get('/api/users/me', TOKEN)
print(f"GET /users/me {code4}:", json.dumps(body4)[:200])

code5, body5 = post('/api/auth/login', {'email':'livetest@example.com','password':'WRONGPASSWORD'})
print(f"BAD LOGIN {code5}:", json.dumps(body5)[:200])

# --- Journey 2: Dashboard ---
print("\n=== JOURNEY 2: DASHBOARD ===")
code, body = get('/api/dashboard/metrics', TOKEN)
print(f"GET /dashboard/metrics {code}:", json.dumps(body)[:400])

# --- Journey 3: Repo Onboarding ---
print("\n=== JOURNEY 3: REPO ONBOARDING ===")
code, body = post('/api/repositories/validate', {'url':'https://github.com/octocat/Hello-World'}, TOKEN)
print(f"VALIDATE {code}:", json.dumps(body)[:300])

code, body = post('/api/repositories', {'url':'https://github.com/octocat/Hello-World'}, TOKEN)
print(f"CREATE REPO {code}:", json.dumps(body)[:300])
if code == 201 and 'data' in body:
    REPO_ID = body['data'].get('id')
    print("REPO_ID:", REPO_ID)

code, body = get('/api/repositories?page=1&pageSize=10', TOKEN)
print(f"LIST REPOS {code}:", json.dumps(body)[:300])

if REPO_ID:
    code, body = get(f'/api/repositories/{REPO_ID}/branches', TOKEN)
    print(f"BRANCHES {code}:", json.dumps(body)[:300])

# --- Journey 4: Scans ---
print("\n=== JOURNEY 4: SCANS ===")
if REPO_ID:
    code, body = post('/api/scans', {'repositoryId': REPO_ID}, TOKEN)
    print(f"TRIGGER SCAN {code}:", json.dumps(body)[:300])
    if code in (200, 201) and 'data' in body:
        SCAN_ID = body['data'].get('id')
        print("SCAN_ID:", SCAN_ID)
    
    if SCAN_ID:
        code, body = get(f'/api/scans/{SCAN_ID}/status', TOKEN)
        print(f"SCAN STATUS {code}:", json.dumps(body)[:300])

# --- Journey 5: Findings + Report ---
print("\n=== JOURNEY 5: FINDINGS + REPORTS ===")
if SCAN_ID:
    code, body = get(f'/api/scans/{SCAN_ID}/findings?page=1&pageSize=10', TOKEN)
    print(f"FINDINGS {code}:", json.dumps(body)[:300])
    if code == 200 and 'data' in body:
        items = body['data'].get('items', [])
        if items: FINDING_ID = items[0]['id']

if FINDING_ID:
    code, body = patch(f'/api/findings/{FINDING_ID}', {'reviewStatus': 'acknowledged', 'reviewNote': 'Verified'}, TOKEN)
    print(f"UPDATE FINDING {code}:", json.dumps(body)[:200])

if SCAN_ID:
    code, body = post('/api/reports', {'scanId': SCAN_ID}, TOKEN)
    print(f"CREATE REPORT {code}:", json.dumps(body)[:300])
    if code in (200, 201) and 'data' in body:
        REPORT_ID = body['data'].get('id')

if REPORT_ID:
    code, body = get(f'/api/reports/{REPORT_ID}', TOKEN)
    print(f"GET REPORT {code}:", json.dumps(body)[:300])

    # Test PDF endpoint
    req_pdf = urllib.request.Request(f'http://127.0.0.1:8000/api/reports/{REPORT_ID}/pdf', headers={'Authorization': 'Bearer ' + (TOKEN or '')})
    try:
        with urllib.request.urlopen(req_pdf, timeout=10) as r:
            ct = r.headers.get('Content-Type', '')
            sz = len(r.read())
            print(f"PDF {r.status}: content-type={ct} size={sz}bytes")
    except urllib.error.HTTPError as e:
        print(f"PDF {e.code}:", e.read().decode()[:200])
