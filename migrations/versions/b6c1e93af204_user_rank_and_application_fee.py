"""user: universitet reytingi oralig'i va ariza to'lovi afzalligi

Revision ID: b6c1e93af204
Revises: a4d7e2b8c516
Create Date: 2026-09-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b6c1e93af204'
down_revision: Union[str, Sequence[str], None] = 'a4d7e2b8c516'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# `op.add_column` enum turini o'zi yaratmaydi — avval qo'lda CREATE TYPE kerak.
rank_range = postgresql.ENUM(
    '1-100', '101-300', '301-500', '500+',
    name='university_rank_range',
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    rank_range.create(op.get_bind(), checkfirst=True)
    op.add_column('users', sa.Column('university_rank_range', rank_range, nullable=True))
    op.add_column('users', sa.Column('application_fee_ok', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'application_fee_ok')
    op.drop_column('users', 'university_rank_range')
    rank_range.drop(op.get_bind(), checkfirst=True)
