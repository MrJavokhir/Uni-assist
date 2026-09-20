"""program notes in 3 languages + structured missing_fields

Revision ID: e7b3d9f21c48
Revises: d5f2a8c61e37
Create Date: 2026-09-20 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b3d9f21c48'
down_revision: Union[str, Sequence[str], None] = 'd5f2a8c61e37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('programs', sa.Column('notes_ru', sa.Text(), nullable=True))
    op.add_column('programs', sa.Column('notes_en', sa.Text(), nullable=True))
    op.add_column('programs', sa.Column('missing_fields', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('programs', 'missing_fields')
    op.drop_column('programs', 'notes_en')
    op.drop_column('programs', 'notes_ru')
