"""Authentication endpoints for login, refresh, password reset."""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import get_db
from core.db.models import User
from core.services.auth_service import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    hash_password,
    verify_password,
)

# Import for type checking only to avoid circular imports
if TYPE_CHECKING:
    from core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request/Response models ───────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserInfo(BaseModel):
    id: str
    email: str
    role: str
    first_name: str | None = None
    last_name: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    user: UserInfo


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str = "If that email exists, a password reset link has been sent."


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=100)


class ResetPasswordResponse(BaseModel):
    message: str = "Password has been reset successfully."


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully."


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a user and return an access token.

    Sets a refresh_token httpOnly cookie for token rotation.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    access_token = create_access_token(user.id, user.role.value, user.organization_id)
    refresh_token = create_refresh_token(user.id)

    # Set refresh token as httpOnly cookie (not accessible from JavaScript)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,  # True in production (HTTPS) — see .env COOKIE_SECURE
        samesite=settings.cookie_samesite,
        max_age=7 * 24 * 60 * 60,  # 7 days in seconds
    )

    return LoginResponse(
        access_token=access_token,
        must_change_password=user.must_change_password,
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            role=user.role.value,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Refresh an access token using a refresh token from httpOnly cookie.

    Returns a new access token and rotates the refresh token.
    """
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        payload = decode_token(refresh_token, "refresh")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Load user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Create new tokens
    new_access_token = create_access_token(user.id, user.role.value, user.organization_id)
    new_refresh_token = create_refresh_token(user.id)

    # Rotate refresh token
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=7 * 24 * 60 * 60,
    )

    return RefreshResponse(
        access_token=new_access_token,
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            role=user.role.value,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response):
    """Clear the refresh token cookie to log out the user."""
    response.delete_cookie(key="refresh_token")
    return LogoutResponse()


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset token.

    Always returns 200 to prevent user enumeration.
    If the email exists, prints the reset token to console (no email sending yet).
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is not None and user.is_active:
        reset_token = create_reset_token(user.id)
        # TODO: Send email with reset link containing the token
        # For now, print to console for development
        reset_origin = settings.cors_origins[0] if settings.cors_origins else "http://localhost:5173"
        print(f"[PASSWORD RESET] Token for {user.email}: {reset_token}")
        print(f"[PASSWORD RESET] Reset link: {reset_origin}/reset-password?token={reset_token}")

    # Always return the same message to prevent user enumeration
    return ForgotPasswordResponse()


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset a user's password using a valid reset token."""
    try:
        payload = decode_token(body.token, "reset")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid reset token")

    # Update password
    user.hashed_password = hash_password(body.new_password)
    user.must_change_password = False
    await db.commit()

    return ResetPasswordResponse()
