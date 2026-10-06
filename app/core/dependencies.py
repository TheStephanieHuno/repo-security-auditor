"""Request dependencies: database session and authenticated user (SRS FR-01, FR-10)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenClaims, decode_access_token
from app.db.models import RevokedToken, User
from app.db.session import get_db

_bearer = HTTPBearer(auto_error=False)

DBSession = Annotated[AsyncSession, Depends(get_db)]


def _unauthorized(message: str = "Authentication required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_token_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DBSession,
) -> TokenClaims:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    claims = decode_access_token(credentials.credentials)
    if claims is None:
        raise _unauthorized("Invalid or expired authentication token.")
    revoked = await db.scalar(select(exists().where(RevokedToken.jti == claims.token_id)))
    if revoked:
        raise _unauthorized("Invalid or expired authentication token.")
    return claims


async def get_current_user(
    claims: Annotated[TokenClaims, Depends(get_token_claims)], db: DBSession
) -> User:
    try:
        public_id = uuid.UUID(claims.subject)
    except ValueError:
        raise _unauthorized("Invalid or expired authentication token.") from None
    user = (await db.execute(select(User).where(User.public_id == public_id))).scalar_one_or_none()
    if user is None:
        raise _unauthorized("Invalid or expired authentication token.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentClaims = Annotated[TokenClaims, Depends(get_token_claims)]
