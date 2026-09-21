"""program: ariza to'lovi va qo'shimcha talablar; university: reyting

Revision ID: c8d4f1a2e657
Revises: b6c1e93af204
Create Date: 2026-09-21 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d4f1a2e657'
down_revision: Union[str, Sequence[str], None] = 'b6c1e93af204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('universities', sa.Column('ranking', sa.Integer(), nullable=True))
    op.add_column('programs', sa.Column('has_application_fee', sa.Boolean(), nullable=True))
    op.add_column(
        'programs', sa.Column('application_fee_amount', sa.Numeric(10, 2), nullable=True)
    )
    op.add_column(
        'programs', sa.Column('application_fee_currency', sa.String(length=3), nullable=True)
    )
    op.add_column('programs', sa.Column('requirements_text', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('programs', 'requirements_text')
    op.drop_column('programs', 'application_fee_currency')
    op.drop_column('programs', 'application_fee_amount')
    op.drop_column('programs', 'has_application_fee')
    op.drop_column('universities', 'ranking')
