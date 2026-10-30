"""Foydalanuvchi: qadamli onboarding o'tilganmi

Onboarding ilgari faqat filtri bo'sh odamga chiqardi. Filtri eski sahifada
to'ldirilgan foydalanuvchi uni hech qachon ko'rmasdi — /start ham profilni
tozalamaydi. Endi har bir hisobga bir marta chiqadi (javoblar oldindan
tanlangan holda), tugatilganda yoki "O'tkazish" bosilganda belgi qo'yiladi.

Revision ID: d8b3f1c2e5a7
Revises: c4d7e2a9b1f6
Create Date: 2026-10-30
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8b3f1c2e5a7"
down_revision: Union[str, None] = "c4d7e2a9b1f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_done", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_done")
