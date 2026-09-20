"""program: required documents + own scholarship

Revision ID: a4d7e2b8c516
Revises: f2a8c05d31e9
Create Date: 2026-09-20 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4d7e2b8c516'
down_revision: Union[str, Sequence[str], None] = 'f2a8c05d31e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('programs', sa.Column('required_documents', sa.JSON(), nullable=True))
    op.add_column('programs', sa.Column('has_scholarship', sa.Boolean(), nullable=True))
    op.add_column('programs', sa.Column('scholarship_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('programs', 'scholarship_url')
    op.drop_column('programs', 'has_scholarship')
    op.drop_column('programs', 'required_documents')
