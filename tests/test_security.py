"""T-07c: unit tests for password hashing (bcrypt, cost factor 12) and JWT
encoding/decoding (SRS FR-01, US-01 acceptance: bcrypt cost >= 12)."""

import base64
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
import pytest

from app.core import security
from app.core.security import (
    PasswordTooLongError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_production_bcrypt_cost_factor_is_12() -> None:
    """tests/conftest.py lowers BCRYPT_ROUNDS for speed, so check the real default
    in a fresh interpreter without that override."""
    environment = {k: v for k, v in os.environ.items() if k != "BCRYPT_ROUNDS"}
    environment["APP_ENV"] = "test"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.core.security import BCRYPT_ROUNDS, hash_password; "
            "print(BCRYPT_ROUNDS); print(hash_password('correct-horse-battery'))",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    rounds, password_hash = result.stdout.split()
    assert rounds == "12"
    assert password_hash.startswith("$2b$12$")


def test_hash_uses_configured_cost_factor() -> None:
    password_hash = hash_password("correct-horse-battery")
    assert password_hash.startswith(f"$2b${security.BCRYPT_ROUNDS:02d}$")
    # A cost-12 hash produced elsewhere (e.g. by production) still verifies.
    cost_12 = bcrypt.hashpw(b"correct-horse-battery", bcrypt.gensalt(rounds=12)).decode()
    assert verify_password("correct-horse-battery", cost_12)
    assert not verify_password("wrong-password", cost_12)


def test_password_hash_is_salted_bcrypt_and_verifies() -> None:
    first = hash_password("correct-horse-battery")
    second = hash_password("correct-horse-battery")
    assert first != second  # unique salt per hash
    assert first.startswith("$2b$")
    assert "correct-horse-battery" not in first
    assert verify_password("correct-horse-battery", first)
    assert not verify_password("wrong-password", first)


def test_password_over_bcrypt_limit_is_rejected_not_truncated() -> None:
    with pytest.raises(PasswordTooLongError):
        hash_password("x" * 73)
    stored = hash_password("x" * 72)
    assert not verify_password("x" * 73, stored)


def test_verify_rejects_malformed_stored_hash() -> None:
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_token_round_trip_carries_subject_and_unique_id() -> None:
    first = decode_access_token(create_access_token("user-1"))
    second = decode_access_token(create_access_token("user-1"))
    assert first is not None and second is not None
    assert first.subject == "user-1"
    assert first.token_id != second.token_id
    assert first.expires_at > datetime.now(timezone.utc)


def _forge(payload: dict, *, key: str = security.SECRET_KEY, algorithm: str = "HS256") -> str:
    return jwt.encode(payload, key, algorithm=algorithm)


def test_expired_tampered_and_wrong_key_tokens_are_rejected() -> None:
    now = datetime.now(timezone.utc)
    base = {"sub": "user-1", "jti": "abc", "type": "access", "iat": now}
    assert decode_access_token(_forge({**base, "exp": now - timedelta(minutes=1)})) is None
    assert decode_access_token(_forge({**base, "exp": now + timedelta(hours=1)}, key="x" * 40)) is None

    token = create_access_token("user-1")
    header, payload, signature = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=="))
    claims["sub"] = "someone-else"
    forged_payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    assert decode_access_token(f"{header}.{forged_payload}.{signature}") is None


def test_unsigned_alg_none_token_is_rejected() -> None:
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {"sub": "user-1", "jti": "abc", "type": "access", "iat": now, "exp": now + 3600}
    encode = lambda part: base64.urlsafe_b64encode(json.dumps(part).encode()).rstrip(b"=").decode()  # noqa: E731
    unsigned = f"{encode({'alg': 'none', 'typ': 'JWT'})}.{encode(payload)}."
    assert decode_access_token(unsigned) is None


def test_tokens_missing_required_claims_are_rejected() -> None:
    now = datetime.now(timezone.utc)
    assert decode_access_token(_forge({"sub": "u", "exp": now + timedelta(hours=1), "type": "access"})) is None
    assert decode_access_token("not.a.jwt") is None
