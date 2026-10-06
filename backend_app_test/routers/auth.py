import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend_app_test.db.session import get_db
from backend_app_test.db.models import User as DBUser
from backend_app_test.core.security import hash_password, verify_password, create_access_token
from backend_app_test.schemas.generated import (
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    User,
    UserRole,
    PasswordResetRequest,
    PasswordResetConfirm,
    GenericSuccess,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def ensure_utc(dt: datetime | None) -> datetime:
    """Ensures datetime always has UTC timezone info for Pydantic."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # 1. Check if user already exists
    existing = await db.execute(select(DBUser).where(DBUser.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    now = datetime.now(timezone.utc)
    user_id = uuid.uuid4()

    new_db_user = DBUser(
        id=user_id,
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role="developer",
        on_scan_completion=True,
        on_scan_failure=True,
        created_at=now,
        updated_at=now,
    )
    db.add(new_db_user)
    await db.commit()
    await db.refresh(new_db_user)

    token = create_access_token(str(user_id))

    user_response = User(
        id=new_db_user.id,
        name=new_db_user.name,
        email=new_db_user.email,
        role=UserRole.developer,
        createdAt=ensure_utc(new_db_user.created_at),
        updatedAt=ensure_utc(new_db_user.updated_at),
    )

    return AuthResponse(
        status="success",
        data={"token": token, "user": user_response}
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBUser).where(DBUser.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(str(user.id))

    role_val = UserRole.developer
    if hasattr(user, "role") and user.role in [r.value for r in UserRole]:
        role_val = UserRole(user.role)

    user_response = User(
        id=user.id,
        name=user.name,
        email=user.email,
        role=role_val,
        createdAt=ensure_utc(user.created_at),
        updatedAt=ensure_utc(user.updated_at),
    )
    return AuthResponse(
        status="success",
        data={"token": token, "user": user_response}
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    return None


@router.post("/password-reset/request", response_model=GenericSuccess)
async def password_reset_request(body: PasswordResetRequest):
    return GenericSuccess(
        status="success",
        data={"message": "If an account exists, reset instructions have been sent."},
    )


@router.post("/password-reset/confirm", response_model=GenericSuccess)
async def password_reset_confirm(body: PasswordResetConfirm):
    return GenericSuccess(
        status="success",
        data={"message": "Password has been reset successfully."},
    )

@router.post("/token", summary="OAuth2 password flow (Swagger UI login)")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Standard OAuth2 password-flow token endpoint.
    Swagger UI sends form fields: username (your email) and password.
    Returns: {"access_token": "<jwt>", "token_type": "bearer"}
    """
    # form_data.username holds the email address in our system
    result = await db.execute(select(DBUser).where(DBUser.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer"}