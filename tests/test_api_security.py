"""RSA-93 (O-16) / RSA-70 (O-15): security test suite (SRS NFR-01, FR-10).

Runs in-process by default. Set RSA_LIVE_BASE_URL (e.g. http://127.0.0.1:8000)
to execute the same suite against a running server; live mode adds a real
public GitHub repository, so it needs network access.
"""

import base64
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
import pytest_asyncio

from tests.conftest import APIHarness

LIVE_URL = os.getenv("RSA_LIVE_BASE_URL")
LIVE_REPOSITORY = os.getenv("RSA_LIVE_REPOSITORY", "https://github.com/octocat/Hello-World")
PUBLIC_ENDPOINTS = {
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/password-reset/request"),
    ("POST", "/api/auth/password-reset/confirm"),
    ("GET", "/api/health"),
}
LEAK_MARKERS = re.compile(r"Traceback|sqlalchemy|sqlite|asyncpg|File \"|\.py\"|SELECT |INSERT ", re.I)


@pytest_asyncio.fixture
async def target(api):
    if LIVE_URL:
        async with httpx.AsyncClient(base_url=LIVE_URL, timeout=60) as client:
            yield APIHarness(client=client, sessions=None, github=None, dispatcher=None)
    else:
        yield api


def unique_email() -> str:
    return f"sec-{uuid.uuid4().hex[:12]}@example.com"


def repository_url() -> str:
    return LIVE_REPOSITORY if LIVE_URL else f"https://github.com/acme/repo-{uuid.uuid4().hex[:8]}"


def assert_error_envelope(response: httpx.Response, status: int) -> None:
    assert response.status_code == status, (response.status_code, response.text[:300])
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] and body["error"]["message"]
    assert not LEAK_MARKERS.search(response.text), response.text[:300]


# -------------------------------------------------- authentication required


@pytest.mark.asyncio
async def test_every_protected_endpoint_requires_authentication(target) -> None:
    spec = (await target.client.get("/api/openapi.json")).json()
    checked = 0
    for path, operations in spec["paths"].items():
        for method in operations:
            if (method.upper(), path) in PUBLIC_ENDPOINTS:
                continue
            url = path.replace("{id}", str(uuid.uuid4()))
            response = await target.client.request(method.upper(), url, json={})
            assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code}"
            assert response.headers.get("www-authenticate", "").lower().startswith("bearer")
            checked += 1
    assert checked >= 25


def _b64(part: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(part).encode()).rstrip(b"=").decode()


@pytest.mark.asyncio
async def test_forged_expired_and_revoked_tokens_are_rejected(target) -> None:
    headers = await target.register(unique_email())
    me = (await target.client.get("/api/users/me", headers=headers)).json()["data"]
    now = datetime.now(timezone.utc)
    claims = {"sub": me["id"], "jti": uuid.uuid4().hex, "type": "access",
              "iat": int(now.timestamp()), "exp": int((now + timedelta(hours=1)).timestamp())}
    forged = [
        "garbage",
        f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(claims)}.",
        jwt.encode(claims, "attacker-chosen-key-that-is-long-enough!!", algorithm="HS256"),
        jwt.encode({**claims, "exp": int((now - timedelta(minutes=5)).timestamp())},
                   "attacker-chosen-key-that-is-long-enough!!", algorithm="HS256"),
    ]
    for token in forged:
        response = await target.client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert_error_envelope(response, 401)
    for scheme in ("Basic dXNlcjpwYXNz", headers["Authorization"].replace("Bearer", "Token")):
        assert (await target.client.get("/api/users/me", headers={"Authorization": scheme})).status_code == 401

    assert (await target.client.post("/api/auth/logout", headers=headers)).status_code == 204
    assert_error_envelope(await target.client.get("/api/users/me", headers=headers), 401)


# ---------------------------------------------------- object-level access


@pytest.mark.asyncio
async def test_users_cannot_read_or_change_each_others_resources(target) -> None:
    owner = await target.register(unique_email())
    intruder = await target.register(unique_email())
    repository = await target.add_repository(owner, repository_url())
    scan = await target.start_scan(owner, repository["id"], branch="master" if LIVE_URL else "main")

    attempts = [
        ("GET", f"/api/repositories/{repository['id']}", None),
        ("GET", f"/api/repositories/{repository['id']}/branches", None),
        ("DELETE", f"/api/repositories/{repository['id']}", None),
        ("GET", f"/api/scans/{scan['id']}", None),
        ("GET", f"/api/scans/{scan['id']}/status", None),
        ("GET", f"/api/scans/{scan['id']}/findings", None),
        ("POST", f"/api/scans/{scan['id']}/cancel", None),
        ("POST", "/api/scans", {"repositoryId": repository["id"], "branch": "main"}),
        ("POST", "/api/reports", {"scanId": scan["id"]}),
    ]
    for method, path, body in attempts:
        response = await target.client.request(method, path, json=body, headers=intruder)
        assert_error_envelope(response, 404)

    for path in (f"/api/scans?repositoryId={repository['id']}", f"/api/findings?scanId={scan['id']}",
                 f"/api/reports?scanId={scan['id']}", "/api/repositories"):
        assert (await target.client.get(path, headers=intruder)).json()["data"] == []
    metrics = (await target.client.get("/api/dashboard/metrics", headers=intruder)).json()["data"]
    assert metrics["repositories"]["total"] == 0 and metrics["scans"]["total"] == 0

    # The owner's resources were not modified by the attempts.
    assert (await target.client.get(f"/api/repositories/{repository['id']}", headers=owner)).status_code == 200
    status = (await target.client.get(f"/api/scans/{scan['id']}", headers=owner)).json()["data"]["status"]
    assert status != "cancelled"


@pytest.mark.asyncio
async def test_registration_ignores_privilege_fields(target) -> None:
    response = await target.client.post(
        "/api/auth/register",
        json={"name": "Mallory", "email": unique_email(), "password": "long-enough-pass",
              "role": "administrator", "id": str(uuid.uuid4())},
    )
    assert response.status_code == 201
    assert response.json()["data"]["user"]["role"] == "developer"


# ------------------------------------------------------- malformed input


@pytest.mark.asyncio
async def test_malformed_bodies_return_validation_errors(target) -> None:
    headers = await target.register(unique_email())
    cases = [
        ("POST", "/api/auth/login", b"{not json", {"Content-Type": "application/json"}),
        ("POST", "/api/auth/login", json.dumps({"email": ["x"], "password": 5}).encode(), {}),
        ("POST", "/api/repositories", json.dumps({"url": None}).encode(), headers),
        ("POST", "/api/scans", json.dumps({"repositoryId": "not-a-uuid", "branch": "main"}).encode(), headers),
        ("PATCH", f"/api/findings/{uuid.uuid4()}", json.dumps({"reviewStatus": "pwned"}).encode(), headers),
    ]
    for method, path, content, extra in cases:
        response = await target.client.request(
            method, path, content=content, headers={"Content-Type": "application/json", **extra}
        )
        assert_error_envelope(response, 422)
        assert "pwned" not in response.text  # submitted values are not echoed back


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/findings?severity=' OR 1=1--",
        "/api/findings?reviewStatus=open;DROP TABLE findings",
        "/api/findings?category=%00",
        "/api/findings?repositoryId=1 OR 1=1",
        "/api/scans?repositoryId=../../etc/passwd",
        "/api/repositories?page=-1",
        "/api/repositories?pageSize=100000",
        "/api/scans/..%2F..%2Fetc%2Fpasswd",
        "/api/findings/1 UNION SELECT password_hash FROM users",
    ],
)
async def test_injection_style_parameters_are_rejected_safely(target, path) -> None:
    headers = await target.register(unique_email())
    response = await target.client.get(path, headers=headers)
    assert response.status_code in {404, 422}, (path, response.status_code)
    assert not LEAK_MARKERS.search(response.text)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data",
        "https://github.com@evil.example.com/acme/web",
        "https://github.com.evil.example.com/acme/web",
        "file:///etc/passwd",
        "https://github.com/acme/web/../../../etc",
        "https://github.com/" + "a" * 5000 + "/b",
        "git@github.com:acme/web.git",
    ],
)
async def test_repository_urls_cannot_target_other_hosts(target, url) -> None:
    headers = await target.register(unique_email())
    response = await target.client.post("/api/repositories", json={"url": url}, headers=headers)
    assert_error_envelope(response, 422)


@pytest.mark.asyncio
async def test_oversized_and_unusual_text_is_handled(target) -> None:
    long_name = await target.client.post(
        "/api/auth/register", json={"name": "n" * 10_000, "email": unique_email(), "password": "long-enough-pass"}
    )
    assert long_name.status_code == 422
    unicode_name = await target.client.post(
        "/api/auth/register",
        json={"name": "Zoë 🛡️ <script>alert(1)</script>", "email": unique_email(), "password": "long-enough-pass"},
    )
    assert unicode_name.status_code == 201
    # Stored as data and returned as JSON, never interpreted.
    assert unicode_name.json()["data"]["user"]["name"] == "Zoë 🛡️ <script>alert(1)</script>"
    assert unicode_name.headers["content-type"].startswith("application/json")


# ---------------------------------------------------- transport hardening


@pytest.mark.asyncio
async def test_security_headers_and_cors_policy(target) -> None:
    response = await target.client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"

    evil = await target.client.options(
        "/api/users/me",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert evil.headers.get("access-control-allow-origin") != "https://evil.example.com"
    assert evil.headers.get("access-control-allow-origin") != "*"
    allowed = await target.client.options(
        "/api/users/me",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_responses_never_expose_password_hashes(target) -> None:
    email = unique_email()
    headers = await target.register(email, password="correct-horse-battery")
    login = await target.client.post("/api/auth/login", json={"email": email, "password": "correct-horse-battery"})
    for response in (login, await target.client.get("/api/users/me", headers=headers)):
        assert "$2b$" not in response.text
        assert "password" not in json.dumps(response.json()["data"]).lower()
