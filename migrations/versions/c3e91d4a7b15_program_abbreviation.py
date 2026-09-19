"""program abbreviation (MBA, LLM, B.Sc.)

Revision ID: c3e91d4a7b15
Revises: a1c4f7b93e20
Create Date: 2026-09-19 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e91d4a7b15'
down_revision: Union[str, Sequence[str], None] = 'a1c4f7b93e20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('programs', sa.Column('abbreviation', sa.String(length=30), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('programs', 'abbreviation')
