"""FastAPI dependencies for authentication and authorization."""
import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import get_db
from core.db.models import User, UserRole
from core.services.auth_service import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT access token.

    Args:
        credentials: The HTTP Bearer token from the Authorization header
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException: 401 if token is invalid/expired, 403 if user is inactive
    """
    token = credentials.credentials

    try:
        payload = decode_token(token, "access")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Inactive user account",
        )

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user has admin role.

    Args:
        current_user: The authenticated user

    Returns:
        The authenticated admin User object

    Raises:
        HTTPException: 403 if user is not an admin
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return current_user


async def require_recruiter(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user has recruiter or admin role.

    Both admin and recruiter roles are allowed.

    Args:
        current_user: The authenticated user

    Returns:
        The authenticated User object

    Raises:
        HTTPException: 403 if user is not a recruiter or admin
    """
    if current_user.role not in (UserRole.admin, UserRole.recruiter):
        raise HTTPException(
            status_code=403,
            detail="Recruiter or admin access required",
        )
    return current_user
