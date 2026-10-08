from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from backend_app_test.core.dependencies import CurrentUser, DBSession
from backend_app_test.core.security import hash_password, verify_password
from backend_app_test.db.models import User as DBUser
from backend_app_test.schemas.generated import (
    User, UserRole, UserResponse, UpdateProfileRequest, ChangePasswordRequest,
    NotificationSettings, NotificationSettingsResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])

def ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    role_str = getattr(current_user, "role", "developer") or "developer"
    role_enum = UserRole(role_str) if role_str in [r.value for r in UserRole] else UserRole.developer
    user_data = User(id=current_user.id, name=current_user.name, email=current_user.email, role=role_enum, createdAt=ensure_utc(current_user.created_at), updatedAt=ensure_utc(current_user.updated_at))
    return UserResponse(status="success", data=user_data)

@router.put("/me", response_model=UserResponse)
async def update_profile(body: UpdateProfileRequest, current_user: CurrentUser, db: DBSession):
    if body.email != current_user.email:
        existing = await db.execute(select(DBUser).where(DBUser.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already taken.")
    current_user.name = body.name
    current_user.email = body.email
    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(current_user)
    role_str = getattr(current_user, "role", "developer") or "developer"
    role_enum = UserRole(role_str) if role_str in [r.value for r in UserRole] else UserRole.developer
    user_data = User(id=current_user.id, name=current_user.name, email=current_user.email, role=role_enum, createdAt=ensure_utc(current_user.created_at), updatedAt=ensure_utc(current_user.updated_at))
    return UserResponse(status="success", data=user_data)

@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: ChangePasswordRequest, current_user: CurrentUser, db: DBSession):
    if not verify_password(body.currentPassword, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password incorrect.")
    current_user.hashed_password = hash_password(body.newPassword)
    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return None

@router.get("/me/settings", response_model=NotificationSettingsResponse)
async def get_settings(current_user: CurrentUser):
    return NotificationSettingsResponse(status="success", data=NotificationSettings(onScanCompletion=bool(current_user.on_scan_completion), onScanFailure=bool(current_user.on_scan_failure)))

@router.put("/me/settings", response_model=NotificationSettingsResponse)
async def save_settings(body: NotificationSettings, current_user: CurrentUser, db: DBSession):
    current_user.on_scan_completion = body.onScanCompletion
    current_user.on_scan_failure = body.onScanFailure
    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return NotificationSettingsResponse(status="success", data=body)
