"""Admin-only endpoints: user management, metrics, cost estimation, CV bank."""
import secrets
import string
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import get_db
from core.db.models import Analysis, CV, Feedback, JobCategory, User, UserRole
from core.dependencies import require_admin
from core.services.auth_service import hash_password
from core.services.cleanup_service import delete_old_analyses
from core.services.ttl_service import expire_old_cvs

router = APIRouter(prefix="/admin", tags=["admin"])

_CV_TTL_DAYS = 120  # 4 months — must match ttl_service


def _random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── User management ───────────────────────────────────────────────────────────


class CreateUserRequest(BaseModel):
    email: EmailStr
    role: UserRole
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class PatchUserRequest(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@router.get("/users")
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    users = (
        await db.execute(select(User).order_by(User.created_at.desc()))
    ).scalars().all()

    result = []
    for u in users:
        # Analyses are org-scoped; use org count as the best available proxy.
        analysis_count: int = (
            await db.execute(
                select(func.count())
                .select_from(Analysis)
                .where(Analysis.organization_id == u.organization_id)
            )
        ).scalar_one()

        result.append(
            {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "role": u.role.value,
                "is_active": u.is_active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat(),
                "analysis_count": analysis_count,
            }
        )
    return result


@router.post("/users", status_code=201)
async def create_user(
    body: CreateUserRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Ya existe un usuario con ese email.")

    temp_password = body.password or _random_password()

    new_user = User(
        email=body.email,
        hashed_password=hash_password(temp_password),
        role=body.role,
        first_name=body.first_name,
        last_name=body.last_name,
        organization_id=current_user.organization_id,
        is_active=True,
        must_change_password=True,
    )
    db.add(new_user)
    await db.commit()

    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role.value,
        "temporary_password": temp_password,
        "must_change_password": True,
    }


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: str,
    body: PatchUserRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "ID de usuario inválido.")

    user = (
        await db.execute(select(User).where(User.id == uid))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "Usuario no encontrado.")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = body.role
    if body.first_name is not None:
        user.first_name = body.first_name
    if body.last_name is not None:
        user.last_name = body.last_name

    await db.commit()
    return {"id": str(user.id), "is_active": user.is_active, "role": user.role.value}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "ID de usuario inválido.")

    user = (
        await db.execute(select(User).where(User.id == uid))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "Usuario no encontrado.")

    new_password = _random_password()
    user.hashed_password = hash_password(new_password)
    user.must_change_password = True
    await db.commit()

    return {"new_password": new_password, "must_change_password": True}


# ── Metrics ───────────────────────────────────────────────────────────────────


async def _compute_analysis_metrics(
    db: AsyncSession, user_id: Optional[_uuid.UUID] = None
) -> dict:
    """Analysis-scoped metrics. When user_id is given, filter to that user."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    def _scope(stmt):
        return stmt.where(Analysis.user_id == user_id) if user_id else stmt

    total_analyses: int = (
        await db.execute(_scope(select(func.count()).select_from(Analysis)))
    ).scalar_one()

    analyses_last_30: int = (
        await db.execute(
            _scope(
                select(func.count())
                .select_from(Analysis)
                .where(Analysis.created_at >= thirty_days_ago)
            )
        )
    ).scalar_one()

    # Group by calendar date (MySQL func.date strips time component).
    day_rows = (
        await db.execute(
            _scope(
                select(
                    func.date(Analysis.created_at).label("date"),
                    func.count().label("count"),
                )
                .where(Analysis.created_at >= thirty_days_ago)
                .group_by(func.date(Analysis.created_at))
                .order_by(func.date(Analysis.created_at))
            )
        )
    ).all()
    analyses_by_day = [{"date": str(r.date), "count": r.count} for r in day_rows]

    cat_stmt = (
        select(
            JobCategory.slug,
            JobCategory.display_name,
            func.count(Analysis.id).label("count"),
        )
        .join(Analysis, Analysis.job_category_id == JobCategory.id)
        .group_by(JobCategory.id, JobCategory.slug, JobCategory.display_name)
        .order_by(func.count(Analysis.id).desc())
        .limit(5)
    )
    if user_id:
        cat_stmt = cat_stmt.where(Analysis.user_id == user_id)
    cat_rows = (await db.execute(cat_stmt)).all()
    top_categories = [
        {"slug": r.slug, "display_name": r.display_name, "count": r.count}
        for r in cat_rows
    ]

    avg_stmt = select(func.avg(Feedback.rating))
    if user_id:
        avg_stmt = avg_stmt.join(
            Analysis, Analysis.id == Feedback.analysis_id
        ).where(Analysis.user_id == user_id)
    avg_rating = (await db.execute(avg_stmt)).scalar_one()

    return {
        "total_analyses": total_analyses,
        "analyses_last_30_days": analyses_last_30,
        "analyses_by_day": analyses_by_day,
        "top_categories": top_categories,
        "average_rating": round(float(avg_rating), 2) if avg_rating else None,
    }


async def _compute_analysis_costs(
    db: AsyncSession, user_id: Optional[_uuid.UUID] = None
) -> dict:
    """Analysis-scoped cost estimation. When user_id is given, filter to that user."""
    stmt = select(func.count()).select_from(Analysis)
    if user_id:
        stmt = stmt.where(Analysis.user_id == user_id)
    total_analyses: int = (await db.execute(stmt)).scalar_one()

    estimated_embedding_calls = total_analyses * _EMBEDDINGS_PER_ANALYSIS

    ranking_cost = total_analyses * _COST_RANKING
    category_cost = total_analyses * _COST_CATEGORY
    contact_cost = total_analyses * _COST_CONTACT
    embedding_cost = estimated_embedding_calls * _COST_EMBEDDING
    total_cost = ranking_cost + category_cost + contact_cost + embedding_cost

    return {
        "total_analyses": total_analyses,
        "estimated_ranking_calls": total_analyses,
        "estimated_category_calls": total_analyses,
        "estimated_contact_extraction_calls": total_analyses,
        "estimated_embedding_calls": estimated_embedding_calls,
        "estimated_total_cost_usd": round(total_cost, 4),
        "cost_breakdown": {
            "ranking": round(ranking_cost, 4),
            "category": round(category_cost, 4),
            "contact": round(contact_cost, 4),
            "embeddings": round(embedding_cost, 4),
        },
    }


@router.get("/metrics")
async def get_metrics(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    three_months_ago = now - timedelta(days=90)
    four_months_ago = now - timedelta(days=_CV_TTL_DAYS)

    analysis_metrics = await _compute_analysis_metrics(db)

    total_cvs: int = (
        await db.execute(select(func.count()).select_from(CV))
    ).scalar_one()

    active_cvs: int = (
        await db.execute(
            select(func.count()).select_from(CV).where(CV.is_expired.is_(False))
        )
    ).scalar_one()

    expiring_soon: int = (
        await db.execute(
            select(func.count())
            .select_from(CV)
            .where(
                and_(
                    CV.is_expired.is_(False),
                    CV.last_seen_at >= four_months_ago,
                    CV.last_seen_at < three_months_ago,
                )
            )
        )
    ).scalar_one()

    expired_cvs: int = (
        await db.execute(
            select(func.count()).select_from(CV).where(CV.is_expired.is_(True))
        )
    ).scalar_one()

    total_users: int = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar_one()

    active_users: int = (
        await db.execute(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        )
    ).scalar_one()

    return {
        **analysis_metrics,
        "total_cvs_in_bank": total_cvs,
        "active_cvs": active_cvs,
        "expiring_soon_cvs": expiring_soon,
        "expired_cvs": expired_cvs,
        "total_users": total_users,
        "active_users": active_users,
    }


# ── Cost estimation ───────────────────────────────────────────────────────────

_COST_RANKING = 0.005
_COST_CATEGORY = 0.001
_COST_CONTACT = 0.001
_COST_EMBEDDING = 0.0001
_EMBEDDINGS_PER_ANALYSIS = 2  # rough estimate


@router.get("/costs")
async def get_costs(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _compute_analysis_costs(db)


# ── Per-user detail ───────────────────────────────────────────────────────────


async def _get_user_or_404(db: AsyncSession, user_id: str) -> User:
    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "ID de usuario inválido.")

    user = (
        await db.execute(select(User).where(User.id == uid))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "Usuario no encontrado.")
    return user


@router.get("/users/{user_id}/metrics")
async def get_user_metrics(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user_or_404(db, user_id)

    if user.first_name or user.last_name:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    else:
        full_name = None

    analysis_metrics = await _compute_analysis_metrics(db, user_id=user.id)

    return {
        "user_id": str(user.id),
        "email": user.email,
        "full_name": full_name,
        **analysis_metrics,
    }


@router.get("/users/{user_id}/costs")
async def get_user_costs(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user_or_404(db, user_id)
    return await _compute_analysis_costs(db, user_id=user.id)


# ── CV bank management ────────────────────────────────────────────────────────


@router.get("/cvs")
async def list_cvs(
    page: int = Query(default=1, ge=1),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page_size = 20
    offset = (page - 1) * page_size
    now = datetime.now(timezone.utc)

    total: int = (
        await db.execute(select(func.count()).select_from(CV))
    ).scalar_one()

    cvs = (
        await db.execute(
            select(CV).order_by(CV.created_at.desc()).offset(offset).limit(page_size)
        )
    ).scalars().all()

    items = []
    for cv in cvs:
        last_seen = cv.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        expiry_date = last_seen + timedelta(days=_CV_TTL_DAYS)
        days_until_expiry = (expiry_date - now).days

        items.append(
            {
                "id": str(cv.id),
                "filename": cv.filename,
                "full_name": cv.full_name,
                "email": cv.email,
                "created_at": cv.created_at.isoformat(),
                "last_seen_at": cv.last_seen_at.isoformat(),
                "times_matched": cv.times_matched,
                "is_expired": cv.is_expired,
                "days_until_expiry": days_until_expiry,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.post("/expire-cvs")
async def admin_expire_cvs(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    count = await expire_old_cvs(db)
    return {"expired": count}


@router.post("/cleanup-analyses")
async def admin_cleanup_analyses(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger deletion of analyses older than 7 days."""
    deleted_count = await delete_old_analyses(db)
    return {"deleted_count": deleted_count}
