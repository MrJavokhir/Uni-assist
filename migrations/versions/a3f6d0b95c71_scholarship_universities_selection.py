"""scholarship: universities, who selects, free-text requirements

Mini App grant oynasida "qaysi universitetda o'qiladi", "kim tanlaydi" va
erkin matnli talablar ko'rsatilishi kerak, lekin bu uchta ma'lumot modelda
umuman yo'q edi. Uchala ustun ham nullable — mavjud yozuvlarga tegilmaydi.

Revision ID: a3f6d0b95c71
Revises: e4b8c2d95f17
Create Date: 2026-09-24 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f6d0b95c71'
down_revision: Union[str, Sequence[str], None] = 'e4b8c2d95f17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNS = (
    # Qaysi universitet(lar)da o'qiladi — konsorsium a'zolari yoki tanlov qoidasi.
    ('universities_text', sa.Text()),
    # Kim tanlaydi: komissiya, elchixona, vazirlik.
    ('selected_by', sa.String(length=255)),
    # Erkin matnli talablar (dasturlardagi requirements_text kabi).
    ('requirements_text', sa.Text()),
)


def upgrade() -> None:
    """Upgrade schema."""
    for name, type_ in COLUMNS:
        op.add_column('scholarships', sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for name, _type in reversed(COLUMNS):
        op.drop_column('scholarships', name)
