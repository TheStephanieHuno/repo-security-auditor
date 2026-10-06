from fastapi import APIRouter, Request, status
from sqlalchemy import exists, func, select

from app.api.serializers import user_to_api
from app.core.dependencies import CurrentClaims, DBSession
from app.core.errors import APIError
from app.core.rate_limit import login_failures
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    PasswordTooLongError,
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.models import RevokedToken, User, UserRole
from app.schemas.generated import (
    AuthResponse,
    GenericSuccess,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DBSession):
    email = _normalize_email(body.email)
    name = body.name.strip()
    if not name or len(name) > 255:
        raise APIError(422, "VALIDATION_ERROR", "Name must be between 1 and 255 characters.")
    if await db.scalar(select(exists().where(func.lower(User.email) == email))):
        raise APIError(409, "EMAIL_IN_USE", "An account with this email already exists.")
    try:
        password_hash = hash_password(body.password)
    except PasswordTooLongError:
        raise APIError(422, "VALIDATION_ERROR", "Password must be at most 72 bytes.") from None
    user = User(name=name, email=email, password_hash=password_hash, role=UserRole.DEVELOPER.value)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return AuthResponse(
        status="success",
        data={"token": create_access_token(str(user.public_id)), "user": user_to_api(user)},
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request, db: DBSession):
    email = _normalize_email(body.email)
    client = request.client.host if request.client else "unknown"
    limiter_key = f"{client}:{email}"
    if login_failures.is_limited(limiter_key):
        raise APIError(429, "RATE_LIMITED", "Too many failed sign-in attempts. Try again later.")
    user = (
        await db.execute(select(User).where(func.lower(User.email) == email))
    ).scalar_one_or_none()
    # Verify against a dummy hash for unknown emails so timing does not reveal accounts.
    valid = verify_password(body.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    if user is None or not valid:
        login_failures.record(limiter_key)
        raise APIError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
    login_failures.reset(limiter_key)
    return AuthResponse(
        status="success",
        data={"token": create_access_token(str(user.public_id)), "user": user_to_api(user)},
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(claims: CurrentClaims, db: DBSession):
    db.add(RevokedToken(jti=claims.token_id, expires_at=claims.expires_at))
    await db.flush()
    return None


@router.post("/password-reset/request", response_model=GenericSuccess)
async def password_reset_request(body: PasswordResetRequest):
    # Same response whether or not the account exists (no account enumeration).
    # Email delivery is post-MVP (US-27), so no token is issued yet.
    return GenericSuccess(
        status="success",
        data={"message": "If an account exists, reset instructions have been sent."},
    )


@router.post("/password-reset/confirm", response_model=GenericSuccess)
async def password_reset_confirm(body: PasswordResetConfirm):
    # No reset tokens are issued until email delivery exists, so none can be valid.
    raise APIError(400, "INVALID_TOKEN", "The reset token is invalid or has expired.")
