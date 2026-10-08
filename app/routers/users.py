from fastapi import APIRouter, Request, status
from sqlalchemy import exists, func, select

from app.api.serializers import user_to_api
from app.core.audit import AuditEvent, AuditOutcome, audit_event
from app.core.dependencies import CurrentUser, DBSession
from app.core.errors import APIError
from app.core.security import PasswordTooLongError, hash_password, verify_password
from app.db.models import User
from app.schemas.generated import (
    ChangePasswordRequest,
    NotificationSettings,
    NotificationSettingsResponse,
    UpdateProfileRequest,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])

# Notification preferences have no persistence model yet; the defaults are
# returned and saving echoes the request without storing it.
DEFAULT_SETTINGS = NotificationSettings(onScanCompletion=True, onScanFailure=True)


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser):
    return UserResponse(status="success", data=user_to_api(user))


@router.put("/me", response_model=UserResponse)
async def update_profile(body: UpdateProfileRequest, user: CurrentUser, db: DBSession):
    name = body.name.strip()
    email = body.email.strip().lower()
    if not name or len(name) > 255:
        raise APIError(422, "VALIDATION_ERROR", "Name must be between 1 and 255 characters.")
    if email != user.email and await db.scalar(
        select(exists().where(func.lower(User.email) == email, User.id != user.id))
    ):
        raise APIError(409, "EMAIL_IN_USE", "An account with this email already exists.")
    user.name = name
    user.email = email
    await db.flush()
    await db.refresh(user)
    return UserResponse(status="success", data=user_to_api(user))


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest, request: Request, user: CurrentUser, db: DBSession
):
    if not verify_password(body.currentPassword, user.password_hash):
        audit_event(
            AuditEvent.PASSWORD_CHANGE_FAILED,
            outcome=AuditOutcome.FAILURE,
            request=request,
            actor_id=user.public_id,
            reason="invalid_current_password",
        )
        raise APIError(400, "INVALID_PASSWORD", "Current password is incorrect.")
    try:
        user.password_hash = hash_password(body.newPassword)
    except PasswordTooLongError:
        raise APIError(422, "VALIDATION_ERROR", "Password must be at most 72 bytes.") from None
    # Commit before auditing so the log never records a change that was not saved.
    await db.commit()
    audit_event(
        AuditEvent.PASSWORD_CHANGED,
        outcome=AuditOutcome.SUCCESS,
        request=request,
        actor_id=user.public_id,
    )
    return None


@router.get("/me/settings", response_model=NotificationSettingsResponse)
async def get_settings(user: CurrentUser):
    return NotificationSettingsResponse(status="success", data=DEFAULT_SETTINGS)


@router.put("/me/settings", response_model=NotificationSettingsResponse)
async def save_settings(body: NotificationSettings, user: CurrentUser):
    return NotificationSettingsResponse(status="success", data=body)
