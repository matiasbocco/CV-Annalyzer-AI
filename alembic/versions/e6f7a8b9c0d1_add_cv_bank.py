"""add cvs and cv_analyses tables

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-29 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cvs: permanent candidate records, deduplicated by text_hash.
    # Scores are NOT here — they live in cv_analyses (per-job).
    op.create_table(
        "cvs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        # TEXT = 64 KB; upgrade to MEDIUMTEXT if CV text exceeds that in prod.
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("times_matched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_seen_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("is_expired", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("text_hash"),
    )
    op.create_index("ix_cvs_text_hash", "cvs", ["text_hash"])
    op.create_index("ix_cvs_last_seen_at", "cvs", ["last_seen_at"])
    op.create_index("ix_cvs_is_expired", "cvs", ["is_expired"])

    # cv_analyses: per-job evaluation results for a CV.
    op.create_table(
        "cv_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cv_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("ranking_position", sa.Integer(), nullable=False),
        sa.Column("nivel", sa.String(20), nullable=False),
        sa.Column("detailed_scores", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("gaps", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "recency_factor_applied",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["cv_id"], ["cvs.id"]),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cv_id", "analysis_id"),
    )
    op.create_index("ix_cv_analyses_cv_id", "cv_analyses", ["cv_id"])
    op.create_index("ix_cv_analyses_analysis_id", "cv_analyses", ["analysis_id"])


def downgrade() -> None:
    op.drop_index("ix_cv_analyses_analysis_id", "cv_analyses")
    op.drop_index("ix_cv_analyses_cv_id", "cv_analyses")
    op.drop_table("cv_analyses")
    op.drop_index("ix_cvs_is_expired", "cvs")
    op.drop_index("ix_cvs_last_seen_at", "cvs")
    op.drop_index("ix_cvs_text_hash", "cvs")
    op.drop_table("cvs")
