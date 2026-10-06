import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.schemas.generated import (
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    User,
    PasswordResetRequest,
    PasswordResetConfirm,
    GenericSuccess,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

MOCK_USER = User(
    id=uuid.uuid4(),
    name="Alex Security",
    email="alex@example.com",
    createdAt=datetime.now(timezone.utc),
    updatedAt=datetime.now(timezone.utc),
)

@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    return AuthResponse(
        status="success",
        data={"token": "mock-jwt-token-xyz123", "user": MOCK_USER},
    )

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    new_user = User(
        id=uuid.uuid4(),
        name=body.name,
        email=body.email,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return AuthResponse(
        status="success",
        data={"token": "mock-jwt-token-xyz123", "user": new_user},
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