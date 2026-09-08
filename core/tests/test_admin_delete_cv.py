"""Tests for DELETE /admin/cvs/{cv_id}.

Requires MySQL to be running and alembic migrations applied.

    pytest core/tests/test_admin_delete_cv.py -v
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from core.db.database import get_db
from core.db.models import Analysis, CV, CVAnalysis, Organization, User, UserRole
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
        select(Organization).where(Organization.name == "Test Org Delete CV")
    )
    org = result.scalar_one_or_none()
    if org is None:
        org = Organization(name="Test Org Delete CV")
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)
    return org


@pytest.fixture
async def admin_user(db_session: AsyncSession, test_org: Organization):
    email = "admin_delete_cv@test.com"
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


@pytest.fixture
def admin_headers(admin_user, test_org):
    token = create_access_token(admin_user.id, admin_user.role.value, test_org.id)
    return {"Authorization": f"Bearer {token}"}


async def _make_cv(db_session: AsyncSession, suffix: str = "") -> CV:
    cv = CV(
        filename=f"test_cv{suffix}.pdf",
        text_content=f"CV content {suffix}",
        text_hash=f"hash_{uuid.uuid4().hex}",
    )
    db_session.add(cv)
    await db_session.commit()
    await db_session.refresh(cv)
    return cv


async def _make_analysis(db_session: AsyncSession, test_org: Organization, admin_user: User) -> Analysis:
    analysis = Analysis(
        job_description="Python developer",
        ranking={},
        job_summary="summary",
        model_used="test-model",
        organization_id=test_org.id,
        user_id=admin_user.id,
    )
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)
    return analysis


async def _make_cv_analysis(
    db_session: AsyncSession, cv: CV, analysis: Analysis
) -> CVAnalysis:
    cv_analysis = CVAnalysis(
        cv_id=cv.id,
        analysis_id=analysis.id,
        score=80,
        ranking_position=1,
        nivel="senior",
        detailed_scores={},
        strengths=[],
        gaps=[],
        recommendations=[],
        summary="Great candidate",
        source="bank",
    )
    db_session.add(cv_analysis)
    await db_session.commit()
    await db_session.refresh(cv_analysis)
    return cv_analysis


@pytest.mark.asyncio
async def test_delete_cv_removes_cv_and_cv_analyses(
    client, db_session, test_org, admin_user, admin_headers
):
    cv = await _make_cv(db_session, "_delete_test")
    analysis = await _make_analysis(db_session, test_org, admin_user)
    cv_analysis = await _make_cv_analysis(db_session, cv, analysis)

    cv_id = str(cv.id)
    cv_analysis_id = cv_analysis.id

    resp = client.delete(f"/admin/cvs/{cv_id}", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] is True
    assert body["cv_id"] == cv_id

    # CV row must be gone
    remaining_cv = (
        await db_session.execute(select(CV).where(CV.id == cv.id))
    ).scalar_one_or_none()
    assert remaining_cv is None

    # CVAnalysis row must be gone too
    remaining_cv_analysis = (
        await db_session.execute(
            select(CVAnalysis).where(CVAnalysis.id == cv_analysis_id)
        )
    ).scalar_one_or_none()
    assert remaining_cv_analysis is None


@pytest.mark.asyncio
async def test_delete_cv_invalid_uuid(client, admin_headers):
    resp = client.delete("/admin/cvs/not-a-uuid", headers=admin_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_cv_not_found(client, admin_headers):
    random_id = str(uuid.uuid4())
    resp = client.delete(f"/admin/cvs/{random_id}", headers=admin_headers)
    assert resp.status_code == 404
