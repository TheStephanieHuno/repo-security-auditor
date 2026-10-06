import os
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError

# Password hashing configuration (Bcrypt cost factor >= 12 for O-02)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)

# JWT configuration (O-01)
SECRET_KEY = os.getenv("SECRET_KEY", "repo-security-auditor-production-grade-secret-key-minimum-256-bits")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

def hash_password(plain_password: str) -> str:
    """Hashes a password using bcrypt with cost factor 12."""
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str) -> str:
    """Generates a signed JWT bearer token containing user_id subject and expiration."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> str | None:
    """Validates and decodes a JWT bearer token, returning user_id."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None