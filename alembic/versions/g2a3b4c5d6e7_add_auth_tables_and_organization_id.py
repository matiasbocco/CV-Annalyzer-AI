"""add auth tables and organization_id

Revision ID: g2a3b4c5d6e7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-18 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "g2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin", "recruiter", name="userrole"), nullable=False),
        sa.Column("organization_id", mysql.CHAR(36), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, default=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    # Add organization_id to cvs table
    op.add_column("cvs", sa.Column("organization_id", mysql.CHAR(36), nullable=True))
    op.create_index("ix_cvs_organization_id", "cvs", ["organization_id"])
    op.create_foreign_key("fk_cvs_organization_id", "cvs", "organizations", ["organization_id"], ["id"])

    # Add organization_id to analyses table
    op.add_column("analyses", sa.Column("organization_id", mysql.CHAR(36), nullable=True))
    op.create_index("ix_analyses_organization_id", "analyses", ["organization_id"])
    op.create_foreign_key("fk_analyses_organization_id", "analyses", "organizations", ["organization_id"], ["id"])


def downgrade() -> None:
    # Remove organization_id from analyses
    op.drop_constraint("fk_analyses_organization_id", "analyses", type_="foreignkey")
    op.drop_index("ix_analyses_organization_id", "analyses")
    op.drop_column("analyses", "organization_id")

    # Remove organization_id from cvs
    op.drop_constraint("fk_cvs_organization_id", "cvs", type_="foreignkey")
    op.drop_index("ix_cvs_organization_id", "cvs")
    op.drop_column("cvs", "organization_id")

    # Drop users table
    op.drop_index("ix_users_organization_id", "users")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")

    # Drop organizations table
    op.drop_table("organizations")
