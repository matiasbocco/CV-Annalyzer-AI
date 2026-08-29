"""Tests for authentication endpoints and functionality.

These tests require MySQL to be running. Start it with:
    net start MySQL80  (as administrator)

Then run the migration:
    alembic upgrade head

Then run the seed script:
    python -m core.scripts.seed_admin

Finally run these tests:
    pytest core/tests/test_auth.py -v
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from core.db.database import Base, get_db
from core.db.models import Organization, User, UserRole
from core.main import app
from core.services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_password,
)

# Test database URL (use a separate test database in production)
TEST_DATABASE_URL = settings.database_url

# Create async engine for tests
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture
async def db_session():
    """Provide a database session for tests."""
    async with TestAsyncSessionLocal() as session:
        yield session


@pytest.fixture
def client(db_session):
    """Provide a test client with database override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def test_org(db_session: AsyncSession):
    """Create a test organization."""
    result = await db_session.execute(
        select(Organization).where(Organization.name == "Test Org")
    )
    org = result.scalar_one_or_none()

    if org is None:
        org = Organization(name="Test Org")
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)

    return org


@pytest.fixture
async def test_admin_user(db_session: AsyncSession, test_org: Organization):
    """Create a test admin user."""
    email = "testadmin@test.com"
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password("TestPassword123!"),
            role=UserRole.admin,
            organization_id=test_org.id,
            is_active=True,
            must_change_password=False,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    return user


@pytest.fixture
async def test_recruiter_user(db_session: AsyncSession, test_org: Organization):
    """Create a test recruiter user."""
    email = "testrecruiter@test.com"
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password("TestPassword123!"),
            role=UserRole.recruiter,
            organization_id=test_org.id,
            is_active=True,
            must_change_password=False,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    return user


@pytest.fixture
async def inactive_user(db_session: AsyncSession, test_org: Organization):
    """Create an inactive test user."""
    email = "inactive@test.com"
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password("TestPassword123!"),
            role=UserRole.recruiter,
            organization_id=test_org.id,
            is_active=False,
            must_change_password=False,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    return user


@pytest.mark.asyncio
async def test_login_valid_credentials(client, test_admin_user):
    """Test login with valid credentials returns 200 and access token."""
    response = client.post(
        "/auth/login",
        json={"email": "testadmin@test.com", "password": "TestPassword123!"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "must_change_password" in data

    # Check that refresh_token cookie is set
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_admin_user):
    """Test login with wrong password returns 401."""
    response = client.post(
        "/auth/login",
        json={"email": "testadmin@test.com", "password": "WrongPassword123!"},
    )

    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_inactive_user(client, inactive_user):
    """Test login with inactive user returns 403."""
    response = client.post(
        "/auth/login",
        json={"email": "inactive@test.com", "password": "TestPassword123!"},
    )

    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_access_protected_endpoint_without_token(client):
    """Test accessing protected endpoint without token returns 401."""
    response = client.get("/categories")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_access_protected_endpoint_with_valid_token(client, test_admin_user, test_org):
    """Test accessing protected endpoint with valid token returns 200."""
    # Create a valid access token
    token = create_access_token(
        test_admin_user.id, test_admin_user.role.value, test_org.id
    )

    response = client.get(
        "/categories", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_recruiter_accessing_admin_endpoint(client, test_recruiter_user, test_org):
    """Test recruiter accessing admin-only endpoint returns 403."""
    # Create a valid access token for recruiter
    token = create_access_token(
        test_recruiter_user.id, test_recruiter_user.role.value, test_org.id
    )

    response = client.post(
        "/admin/expire-cvs", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_flow(client, test_admin_user):
    """Test refresh token flow returns new access token."""
    # First login to get refresh token
    login_response = client.post(
        "/auth/login",
        json={"email": "testadmin@test.com", "password": "TestPassword123!"},
    )

    assert login_response.status_code == 200
    refresh_token = login_response.cookies.get("refresh_token")
    assert refresh_token is not None

    # Use refresh token to get new access token
    refresh_response = client.post(
        "/auth/refresh",
        cookies={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Check that a new refresh token was set
    new_refresh_token = refresh_response.cookies.get("refresh_token")
    assert new_refresh_token is not None
    assert new_refresh_token != refresh_token  # Token should be rotated


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
