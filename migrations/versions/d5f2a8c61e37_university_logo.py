"""university logo_url

Revision ID: d5f2a8c61e37
Revises: c3e91d4a7b15
Create Date: 2026-09-19 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5f2a8c61e37'
down_revision: Union[str, Sequence[str], None] = 'c3e91d4a7b15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('universities', sa.Column('logo_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('universities', 'logo_url')
