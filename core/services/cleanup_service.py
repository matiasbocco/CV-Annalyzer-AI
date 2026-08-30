"""
Cleanup service for time-limited data.

Only analyses (and their dependent rows) have a TTL.
The CV bank has its own separate TTL managed by ttl_service.py.

Cascade strategy — manual, not DB-level
----------------------------------------
The FK constraints on cv_analyses, feedback, and tiebreaker_sessions were
created without ON DELETE CASCADE (Alembic default).  Rather than dropping and
recreating those constraints (which requires knowing their auto-generated names),
we delete child rows explicitly in dependency order before removing the parent.
This is equally safe and far simpler to reason about.

Deletion order:
  1. tiebreaker_sessions  (references analyses.id)
  2. feedback             (references analyses.id)
  3. cv_analyses          (references analyses.id AND cvs.id — delete here removes
                           the join record only; the cv row itself is untouched)
  4. analyses             (parent — safe to delete once children are gone)

The cvs table is intentionally NOT touched here; CV-bank TTL is handled
separately by expire_old_cvs().
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import Analysis, CVAnalysis, Feedback, TiebreakerSession

log = logging.getLogger(__name__)

_DEFAULT_MAX_AGE_DAYS = 7


async def delete_old_analyses(
    db: AsyncSession,
    max_age_days: int = _DEFAULT_MAX_AGE_DAYS,
) -> int:
    """Delete Analysis rows (and their dependants) older than *max_age_days*.

    Returns the count of deleted analyses.
    Does NOT touch the CV bank.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    old_ids = (
        await db.execute(
            select(Analysis.id).where(Analysis.created_at < cutoff)
        )
    ).scalars().all()

    if not old_ids:
        return 0

    # Delete dependants first to respect FK constraints, then the parent.
    await db.execute(
        delete(TiebreakerSession).where(TiebreakerSession.analysis_id.in_(old_ids))
    )
    await db.execute(
        delete(Feedback).where(Feedback.analysis_id.in_(old_ids))
    )
    await db.execute(
        delete(CVAnalysis).where(CVAnalysis.analysis_id.in_(old_ids))
    )
    await db.execute(
        delete(Analysis).where(Analysis.id.in_(old_ids))
    )
    await db.commit()

    count = len(old_ids)
    log.info("Deleted %d analyse(s) older than %d days.", count, max_age_days)
    return count
