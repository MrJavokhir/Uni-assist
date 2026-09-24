"""scholarship: universities/selected_by/requirements matnlari uch tilda

Mini App grant oynasida bu uchta maydon faqat bitta tilda ko'rinardi.
`description` bilan bir xil qoida: asosiy ustun o'zbekcha, `_ru`/`_en`
bo'sh bo'lsa interfeys o'zbekchasiga qaytadi.

Revision ID: b7c2e58a04d3
Revises: a3f6d0b95c71
Create Date: 2026-09-24 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c2e58a04d3'
down_revision: Union[str, Sequence[str], None] = 'a3f6d0b95c71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNS = (
    ('universities_text_ru', sa.Text()),
    ('universities_text_en', sa.Text()),
    ('selected_by_ru', sa.String(length=255)),
    ('selected_by_en', sa.String(length=255)),
    ('requirements_text_ru', sa.Text()),
    ('requirements_text_en', sa.Text()),
)


def upgrade() -> None:
    """Upgrade schema."""
    for name, type_ in COLUMNS:
        op.add_column('scholarships', sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for name, _type in reversed(COLUMNS):
        op.drop_column('scholarships', name)
