import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.schemas.generated import (
    User,
    UserResponse,
    UpdateProfileRequest,
    ChangePasswordRequest,
    NotificationSettings,
    NotificationSettingsResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])

CURRENT_USER = User(
    id=uuid.uuid4(),
    name="Alex Security",
    email="alex@example.com",
    createdAt=datetime.now(timezone.utc),
    updatedAt=datetime.now(timezone.utc),
)

@router.get("/me", response_model=UserResponse)
async def get_me():
    return UserResponse(status="success", data=CURRENT_USER)

@router.put("/me", response_model=UserResponse)
async def update_profile(body: UpdateProfileRequest):
    CURRENT_USER.name = body.name
    CURRENT_USER.email = body.email
    CURRENT_USER.updatedAt = datetime.now(timezone.utc)
    return UserResponse(status="success", data=CURRENT_USER)

@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: ChangePasswordRequest):
    return None

@router.get("/me/settings", response_model=NotificationSettingsResponse)
async def get_settings():
    return NotificationSettingsResponse(
        status="success",
        data=NotificationSettings(onScanCompletion=True, onScanFailure=True),
    )

@router.put("/me/settings", response_model=NotificationSettingsResponse)
async def save_settings(body: NotificationSettings):
    return NotificationSettingsResponse(status="success", data=body)