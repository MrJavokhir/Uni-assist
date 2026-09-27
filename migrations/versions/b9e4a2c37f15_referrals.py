"""Taklif (referal) dasturi

Taklif havolasi bilan kelgan yangi foydalanuvchida `referred_by_id`
yoziladi. Mukofot obunadan KEYIN beriladi, shuning uchun "kim taklif
qilgan" va "pul berilgan" alohida maydonlarda turadi.

Mukofot summasi `payment_settings` da: uni o'zgartirish yoki dasturni
to'xtatish (0 qilib qo'yish) uchun deploy kerak bo'lmasligi kerak.

Revision ID: b9e4a2c37f15
Revises: a7c5e91b3d84
Create Date: 2026-09-28
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b9e4a2c37f15"
down_revision: Union[str, None] = "a7c5e91b3d84"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `ALTER TYPE ... ADD VALUE` eski Postgres'da tranzaksiya ichida
    # ishlamaydi, shuning uchun alohida (autocommit) bajariladi.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE transaction_kind ADD VALUE IF NOT EXISTS 'referral'")

    op.add_column(
        "users", sa.Column("referred_by_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "referral_rewarded", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_foreign_key(
        "fk_users_referred_by_id",
        "users",
        "users",
        ["referred_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_referred_by_id", "users", ["referred_by_id"])

    op.add_column(
        "payment_settings",
        sa.Column(
            "referral_bonus",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="1000",
        ),
    )


def downgrade() -> None:
    op.drop_column("payment_settings", "referral_bonus")
    op.drop_index("ix_users_referred_by_id", table_name="users")
    op.drop_constraint("fk_users_referred_by_id", "users", type_="foreignkey")
    op.drop_column("users", "referral_rewarded")
    op.drop_column("users", "referred_by_id")
    # `transaction_kind` dagi 'referral' qiymati QOLDIRILADI: Postgres enum
    # qiymatini o'chirishni qo'llab-quvvatlamaydi, butun turni qayta
    # yaratish esa unga bog'langan ustunlarni ham qayta yozishni talab
    # qiladi. Ishlatilmayotgan qiymat hech narsaga xalaqit bermaydi.
