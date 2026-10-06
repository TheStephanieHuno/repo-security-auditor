"""T-07d: integration tests for POST /api/auth/register and POST /api/auth/login,
plus logout, password change, and password-reset behaviour (SRS FR-01)."""

import pytest


@pytest.mark.asyncio
async def test_register_returns_token_and_user_without_secrets(api) -> None:
    response = await api.client.post(
        "/api/auth/register",
        json={"name": "Ada", "email": "Ada@Example.com", "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    user = body["data"]["user"]
    assert user["email"] == "ada@example.com"
    assert user["role"] == "developer"
    assert "password" not in response.text and "$2b$" not in response.text

    me = await api.client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {body['data']['token']}"}
    )
    assert me.status_code == 200
    assert me.json()["data"]["id"] == user["id"]


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email_case_insensitively(api) -> None:
    await api.register("ada@example.com")
    response = await api.client.post(
        "/api/auth/register",
        json={"name": "Other", "email": "ADA@example.com", "password": "another-password"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_IN_USE"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Ada", "email": "ada@example.com", "password": "short"},
        {"name": "Ada", "email": "not-an-email", "password": "long-enough-pass"},
        {"name": "", "email": "ada@example.com", "password": "long-enough-pass"},
        {"name": "Ada", "email": "ada@example.com", "password": "x" * 100},
        {"email": "ada@example.com", "password": "long-enough-pass"},
    ],
)
async def test_register_validates_input(api, payload) -> None:
    response = await api.client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_login_success_and_uniform_failure_message(api) -> None:
    await api.register("ada@example.com", password="correct-horse-battery")

    ok = await api.client.post(
        "/api/auth/login", json={"email": "ADA@example.com", "password": "correct-horse-battery"}
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["token"]

    wrong_password = await api.client.post(
        "/api/auth/login", json={"email": "ada@example.com", "password": "wrong-password"}
    )
    unknown_user = await api.client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"}
    )
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()  # no account enumeration


@pytest.mark.asyncio
async def test_repeated_login_failures_are_rate_limited(api) -> None:
    await api.register("ada@example.com", password="correct-horse-battery")
    for _ in range(5):
        response = await api.client.post(
            "/api/auth/login", json={"email": "ada@example.com", "password": "wrong-password"}
        )
        assert response.status_code == 401
    blocked = await api.client.post(
        "/api/auth/login", json={"email": "ada@example.com", "password": "correct-horse-battery"}
    )
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_logout_revokes_the_token(api) -> None:
    headers = await api.register("ada@example.com")
    assert (await api.client.post("/api/auth/logout", headers=headers)).status_code == 204
    assert (await api.client.get("/api/users/me", headers=headers)).status_code == 401
    # A fresh login still works.
    login = await api.client.post(
        "/api/auth/login", json={"email": "ada@example.com", "password": "correct-horse-battery"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_requires_current_password(api) -> None:
    headers = await api.register("ada@example.com", password="correct-horse-battery")
    wrong = await api.client.put(
        "/api/users/me/password",
        json={"currentPassword": "nope-nope", "newPassword": "new-password-123"},
        headers=headers,
    )
    assert wrong.status_code == 400
    ok = await api.client.put(
        "/api/users/me/password",
        json={"currentPassword": "correct-horse-battery", "newPassword": "new-password-123"},
        headers=headers,
    )
    assert ok.status_code == 204
    login = await api.client.post(
        "/api/auth/login", json={"email": "ada@example.com", "password": "new-password-123"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_does_not_reveal_accounts(api) -> None:
    await api.register("ada@example.com")
    known = await api.client.post("/api/auth/password-reset/request", json={"email": "ada@example.com"})
    unknown = await api.client.post("/api/auth/password-reset/request", json={"email": "x@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    confirm = await api.client.post(
        "/api/auth/password-reset/confirm", json={"token": "guess", "newPassword": "new-password-123"}
    )
    assert confirm.status_code == 400
