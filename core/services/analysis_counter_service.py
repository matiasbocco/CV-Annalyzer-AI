"""Persistent lifetime counters for analyses.

Why this exists:
  `list_users`, `_compute_analysis_metrics`, and `_compute_analysis_costs`
  used to compute "total analyses" with a live COUNT(*) over the
  `analyses` table. That number naturally shrinks whenever
  cleanup_service purges old rows (30-day retention) — which is correct
  for time-windowed stats like "last 30 days" or "top categories", but
  wrong for a lifetime tally: a user's total shouldn't drop just because
  their old history aged out of the retention window.

These counters are incremented once, at analysis-creation time, and
never decremented — they are the source of truth for "total analyses"
both per-user (User.total_analyses_count) and globally
(AnalysisCounter, a singleton row with id=1), independent of how many
rows still exist in `analyses`.
"""
import uuid as _uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import AnalysisCounter, User


async def increment_analysis_counters(db: AsyncSession, user_id: str | None) -> None:
    """Increment the global lifetime counter, and the per-user one if applicable.

    Does NOT commit — call this within the same transaction as the
    Analysis insert so the counters and the row are created atomically.
    """
    await db.execute(
        update(AnalysisCounter)
        .where(AnalysisCounter.id == 1)
        .values(total_count=AnalysisCounter.total_count + 1)
    )
    if user_id:
        await db.execute(
            update(User)
            .where(User.id == _uuid.UUID(user_id))
            .values(total_analyses_count=User.total_analyses_count + 1)
        )
