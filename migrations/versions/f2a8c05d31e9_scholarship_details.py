"""scholarship details: requirements, stipend range, logo, i18n description

Revision ID: f2a8c05d31e9
Revises: e7b3d9f21c48
Create Date: 2026-09-20 19:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a8c05d31e9'
down_revision: Union[str, Sequence[str], None] = 'e7b3d9f21c48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNS = (
    ('description_ru', sa.Text()),
    ('description_en', sa.Text()),
    ('logo_url', sa.String(length=500)),
    ('stipend_max', sa.Numeric(10, 2)),
    ('stipend_period', sa.String(length=10)),
    ('ielts_min', sa.Numeric(2, 1)),
    ('toefl_min', sa.Integer()),
    ('work_experience_years', sa.Integer()),
    ('degree_levels', sa.JSON()),
    ('study_language', sa.String(length=100)),
    ('duration_min_years', sa.Numeric(3, 1)),
    ('duration_max_years', sa.Numeric(3, 1)),
    ('selection_stages', sa.Integer()),
)


def upgrade() -> None:
    """Upgrade schema."""
    for name, type_ in COLUMNS:
        op.add_column('scholarships', sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for name, _ in reversed(COLUMNS):
        op.drop_column('scholarships', name)
