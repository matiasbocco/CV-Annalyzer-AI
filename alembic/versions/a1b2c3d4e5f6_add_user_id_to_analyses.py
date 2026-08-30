"""add user_id to analyses

Revision ID: a1b2c3d4e5f6
Revises: 67eec85d566e
Create Date: 2026-08-29 00:00:00.000000

Why nullable?
  Existing rows predate the authentication system — there is no way to know
  which user created them.  Making the column NOT NULL would require a default
  value that doesn't exist, or a destructive migration that deletes old data.
  Nullable is the only backwards-compatible option.

Why SET NULL on user delete?
  If a user account is removed we prefer to keep the analysis history
  (visible to admins) rather than cascade-deleting it.  The row becomes
  "orphaned" (user_id = NULL) rather than lost.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "67eec85d566e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("user_id", mysql.CHAR(36), nullable=True),
    )
    op.create_index("ix_analyses_user_id", "analyses", ["user_id"])
    op.create_foreign_key(
        "fk_analyses_user_id",
        "analyses",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_analyses_user_id", "analyses", type_="foreignkey")
    op.drop_index("ix_analyses_user_id", "analyses")
    op.drop_column("analyses", "user_id")
