"""add contact fields to cvs

Revision ID: f1a2b3c4d5e6
Revises: e6f7a8b9c0d1
Create Date: 2026-04-29 21:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cvs", sa.Column("full_name", sa.String(200), nullable=True))
    op.add_column("cvs", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("cvs", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("cvs", sa.Column("linkedin_url", sa.String(500), nullable=True))
    op.add_column("cvs", sa.Column("github_url", sa.String(500), nullable=True))
    op.add_column("cvs", sa.Column("portfolio_url", sa.String(500), nullable=True))
    op.add_column("cvs", sa.Column("location", sa.String(200), nullable=True))
    op.add_column("cvs", sa.Column("availability", sa.String(20), nullable=True))
    op.add_column("cvs", sa.Column("contact_extracted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("cvs", "contact_extracted_at")
    op.drop_column("cvs", "availability")
    op.drop_column("cvs", "location")
    op.drop_column("cvs", "portfolio_url")
    op.drop_column("cvs", "github_url")
    op.drop_column("cvs", "linkedin_url")
    op.drop_column("cvs", "phone")
    op.drop_column("cvs", "email")
    op.drop_column("cvs", "full_name")
