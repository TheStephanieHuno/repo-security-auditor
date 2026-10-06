"""Password hashing and JWT access tokens (SRS FR-01).

Ported from Louis's ``backend_app_test/core/security.py`` design (bcrypt cost
12, HS256 bearer tokens) onto maintained libraries (``bcrypt``, ``PyJWT``),
with a revocable token ID (``jti``) so sign-out invalidates the token.
"""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))
MAX_PASSWORD_BYTES = 72  # bcrypt ignores everything after 72 bytes
MIN_SECRET_KEY_LENGTH = 32
_DEVELOPMENT_ENVIRONMENTS = {"development", "test", "local"}


def _load_secret_key() -> str:
    configured = os.getenv("SECRET_KEY", "")
    if len(configured) >= MIN_SECRET_KEY_LENGTH:
        return configured
    environment = os.getenv("APP_ENV", "development").lower()
    if environment not in _DEVELOPMENT_ENVIRONMENTS:
        raise RuntimeError(
            f"SECRET_KEY must be set to at least {MIN_SECRET_KEY_LENGTH} characters "
            f"when APP_ENV={environment}"
        )
    logger.warning("SECRET_KEY not set; using a random per-process key (tokens reset on restart)")
    return secrets.token_urlsafe(48)


SECRET_KEY = _load_secret_key()


class PasswordTooLongError(ValueError):
    pass


def _encode_password(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
    return encoded


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode_password(password), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_encode_password(password), password_hash.encode("ascii"))
    except ValueError:  # over-long input or a malformed stored hash
        return False


# A real hash to compare against when the account does not exist, so login
# timing does not reveal which emails are registered.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    token_id: str
    expires_at: datetime


def create_access_token(subject: str, *, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenClaims | None:
    """Validate signature, expiry, and required claims; None for any invalid token."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],  # never accept "none" or an attacker-chosen algorithm
            options={"require": ["sub", "jti", "exp", "iat"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    return TokenClaims(
        subject=str(payload["sub"]),
        token_id=str(payload["jti"]),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )
