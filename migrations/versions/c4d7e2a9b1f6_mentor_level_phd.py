"""Uni Buddy: PhD darajasi

QA: savol formasida faqat Bakalavr va Magistratura bor edi — doktoranturaga
qiziquvchi foydalanuvchi o'zini qaysi biriga yozishini bilmasdi.

Revision ID: c4d7e2a9b1f6
Revises: f6a1c3e8b250
Create Date: 2026-10-29
"""

from typing import Union

from alembic import op

revision: str = "c4d7e2a9b1f6"
down_revision: Union[str, None] = "f6a1c3e8b250"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `ALTER TYPE ... ADD VALUE` eski Postgres'da tranzaksiya ichida
    # ishlamaydi, shuning uchun alohida (autocommit) bajariladi.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE mentor_level ADD VALUE IF NOT EXISTS 'phd'")


def downgrade() -> None:
    # Postgres enum qiymatini o'chirishni qo'llab-quvvatlamaydi; ishlatilmayotgan
    # 'phd' qiymati hech narsaga xalaqit bermaydi.
    pass
