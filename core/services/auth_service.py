"""Authentication service for password hashing and JWT token management."""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash

    Returns:
        The bcrypt hash of the password as a string
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The plaintext password to check
        hashed_password: The stored bcrypt hash (as string)

    Returns:
        True if the password matches, False otherwise
    """
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(user_id: uuid.UUID, role: str, organization_id: uuid.UUID) -> str:
    """Create a JWT access token that expires in 1 hour.

    Args:
        user_id: The user's UUID
        role: The user's role (admin or recruiter)
        organization_id: The user's organization UUID

    Returns:
        A signed JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "org_id": str(organization_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a JWT refresh token that expires in 7 days.

    Args:
        user_id: The user's UUID

    Returns:
        A signed JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_reset_token(user_id: uuid.UUID) -> str:
    """Create a JWT password reset token that expires in 1 hour.

    Args:
        user_id: The user's UUID

    Returns:
        A signed JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "reset",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode
        expected_type: The expected token type (access, refresh, or reset)

    Returns:
        The decoded token payload as a dict

    Raises:
        JWTError: If the token is invalid, expired, or has the wrong type
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        if token_type != expected_type:
            raise JWTError(f"Invalid token type: expected {expected_type}, got {token_type}")
        return payload
    except JWTError:
        raise
