"""add persistent analysis counters (users.total_analyses_count, analysis_counters)

Revision ID: c9d0e1f2a3b4
Revises: b2c3d4e5f6a7
Create Date: 2026-09-16 00:00:00.000000

Why: total_analyses (per-user and global) used to be a live COUNT(*) over
`analyses`, which shrinks whenever cleanup_service purges rows older than
the retention window. This adds persistent counters that only increase.

Backfill note: the backfill can only count rows that still exist in
`analyses` at migration time. Analyses already purged by the retention
job before this migration ran are not recoverable — counts start
accurate from here forward, not as a true all-time historical total.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Per-user persistent counter.
    op.add_column(
        "users",
        sa.Column("total_analyses_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        """
        UPDATE users
        SET total_analyses_count = (
            SELECT COUNT(*) FROM analyses WHERE analyses.user_id = users.id
        )
        """
    )

    # 2. Global persistent counter (singleton row, id=1).
    op.create_table(
        "analysis_counters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO analysis_counters (id, total_count) VALUES (1, (SELECT COUNT(*) FROM analyses))"
    )


def downgrade() -> None:
    op.drop_table("analysis_counters")
    op.drop_column("users", "total_analyses_count")
