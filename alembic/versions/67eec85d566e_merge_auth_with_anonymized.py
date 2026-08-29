"""merge auth with anonymized

Revision ID: 67eec85d566e
Revises: a7b8c9d0e1f2, g2a3b4c5d6e7
Create Date: 2026-08-25 10:44:22.067081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67eec85d566e'
down_revision: Union[str, Sequence[str], None] = ('a7b8c9d0e1f2', 'g2a3b4c5d6e7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
