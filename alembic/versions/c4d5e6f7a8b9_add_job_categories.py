"""add job_categories table and job_category_id to analyses

Revision ID: c4d5e6f7a8b9
Revises: b3e9f1a2c4d5
Create Date: 2026-04-27 21:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3e9f1a2c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.add_column(
        "analyses",
        sa.Column("job_category_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_analyses_job_category",
        "analyses",
        "job_categories",
        ["job_category_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_analyses_job_category", "analyses", type_="foreignkey")
    op.drop_column("analyses", "job_category_id")
    op.drop_table("job_categories")
