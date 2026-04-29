"""
TTL (time-to-live) enforcement for the CV bank.

Why run expire_old_cvs on startup rather than a cron job?

For this project's deployment model (single-process uvicorn), startup is the
simplest guaranteed execution point that doesn't require an external scheduler
(cron, Celery beat, APScheduler).  The downside — CVs can be "stale" for up to
one restart cycle — is acceptable because:
  a) The 4-month window is coarse; a few hours of drift is irrelevant.
  b) expired CVs are filtered client-side at query time with is_expired=False,
     so they never appear in results even before the next startup.

A POST /admin/expire-cvs endpoint is also provided for manual triggering
without a restart (e.g., during maintenance or after bulk imports).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import CV
from core.services import vector_service

log = logging.getLogger(__name__)

_EXPIRY_MONTHS = 4


async def expire_old_cvs(db: AsyncSession, threshold_months: int = _EXPIRY_MONTHS) -> int:
    """Mark CVs as expired where last_seen_at < now - threshold_months.

    Also updates ChromaDB metadata so that is_expired=True filters take effect
    in vector search without requiring a MySQL join.

    Returns the count of newly-expired CVs.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_months * 30)

    # Find candidates to expire (only those not already expired).
    result = await db.execute(
        select(CV).where(CV.is_expired.is_(False), CV.last_seen_at < cutoff)
    )
    cvs_to_expire: list[CV] = list(result.scalars().all())

    if not cvs_to_expire:
        return 0

    for cv in cvs_to_expire:
        cv.is_expired = True

    await db.commit()

    # Mirror the flag in ChromaDB so vector searches see it immediately.
    for cv in cvs_to_expire:
        await asyncio.to_thread(
            vector_service.update_metadata,
            str(cv.id),
            {"is_expired": True},
        )

    count = len(cvs_to_expire)
    log.info("Expired %d CV(s) older than %d months.", count, threshold_months)
    return count
