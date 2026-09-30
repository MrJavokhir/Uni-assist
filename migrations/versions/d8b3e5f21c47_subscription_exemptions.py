"""Majburiy obunadan ozod foydalanuvchilar

Telegram ID bo'yicha ishlaydi va `users` ga bog'lanmagan: odam hali botga
kirmagan bo'lsa ham uni oldindan ozod qilib qo'yish mumkin.

Revision ID: d8b3e5f21c47
Revises: c4d7f0a82b93
Create Date: 2026-09-30
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8b3e5f21c47"
down_revision: Union[str, None] = "c4d7f0a82b93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_exemptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        # Bitta odam ro'yxatda ikki marta turmasin: aks holda birini
        # o'chirib, ikkinchisi qolib ketardi va ozodlik saqlanaverardi.
        sa.UniqueConstraint("telegram_id", name="uq_subscription_exemptions_telegram_id"),
    )


def downgrade() -> None:
    op.drop_table("subscription_exemptions")
