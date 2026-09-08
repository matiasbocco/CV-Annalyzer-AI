"""Tests for per-user admin detail endpoints (metrics + costs).

These tests require MySQL to be running. Start it with:
    net start MySQL80  (as administrator)

Then run the migration:
    alembic upgrade head

Finally run these tests:
    pytest core/tests/test_admin_user_detail.py -v
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from core.db.database import get_db
from core.db.models import Analysis, Organization, User, UserRole
from core.main import app
from core.services.auth_service import create_access_token, hash_password

TEST_DATABASE_URL = settings.database_url

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture
async def db_session():
    async with TestAsyncSessionLocal() as session:
        yield session


@pytest.fixture
def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def test_org(db_session: AsyncSession):
    result = await db_session.execute(
        select(Organization).where(Organization.name == "Test Org Detail")
    )
    org = result.scalar_one_or_none()
    if org is None:
        org = Organization(name="Test Org Detail")
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)
    return org


@pytest.fixture
async def admin_user(db_session: AsyncSession, test_org: Organization):
    email = "admin_detail@test.com"
    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
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


async def _make_user(db_session, org, email, first_name):
    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password("TestPassword123!"),
            role=UserRole.recruiter,
            organization_id=org.id,
            is_active=True,
            must_change_password=False,
            first_name=first_name,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    return user


async def _make_analyses(db_session, org, user, count):
    for _ in range(count):
        db_session.add(
            Analysis(
                job_description="jd",
                ranking={},
                job_summary="summary",
                model_used="test-model",
                organization_id=org.id,
                user_id=user.id,
            )
        )
    await db_session.commit()


@pytest.fixture
def admin_headers(admin_user, test_org):
    token = create_access_token(admin_user.id, admin_user.role.value, test_org.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_user_metrics_and_costs_are_scoped(
    client, db_session, test_org, admin_headers
):
    user_a = await _make_user(db_session, test_org, "detail_a@test.com", "Alice")
    user_b = await _make_user(db_session, test_org, "detail_b@test.com", "Bob")

    await _make_analyses(db_session, test_org, user_a, 3)
    await _make_analyses(db_session, test_org, user_b, 5)

    # ── Metrics for user_a ────────────────────────────────────────────────
    resp = client.get(f"/admin/users/{user_a.id}/metrics", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(user_a.id)
    assert data["email"] == "detail_a@test.com"
    assert data["full_name"] == "Alice"
    assert data["total_analyses"] == 3  # only user_a's analyses, not user_b's

    # ── Costs for user_a ──────────────────────────────────────────────────
    resp = client.get(f"/admin/users/{user_a.id}/costs", headers=admin_headers)
    assert resp.status_code == 200
    costs_a = resp.json()
    assert costs_a["total_analyses"] == 3

    # ── user_b sees only its own 5 ────────────────────────────────────────
    resp = client.get(f"/admin/users/{user_b.id}/costs", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total_analyses"] == 5


@pytest.mark.asyncio
async def test_user_metrics_invalid_uuid_returns_400(client, admin_headers):
    resp = client.get("/admin/users/not-a-uuid/metrics", headers=admin_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_user_metrics_unknown_user_returns_404(client, admin_headers):
    resp = client.get(f"/admin/users/{uuid.uuid4()}/metrics", headers=admin_headers)
    assert resp.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
