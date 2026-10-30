"""Onboarding har 3 kunda qayta o'tiladi

`onboarding_done` belgisi o'rniga onboarding o'tilgan vaqt saqlanadi; u 3 kun
amal qiladi (app/webapp/api.py: ONBOARDING_VALID_FOR). Hozirgi
foydalanuvchilarniki nolga tushadi — Mini App'ni keyingi ochishda onboarding
yana chiqadi.

Revision ID: b5d1e8f3a2c6
Revises: a7e3c9d1b4f8
Create Date: 2026-10-30
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5d1e8f3a2c6"
down_revision: Union[str, None] = "a7e3c9d1b4f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("onboarding_done_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.drop_column("users", "onboarding_done")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_done", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE users SET onboarding_done = true WHERE onboarding_done_at IS NOT NULL")
    op.drop_column("users", "onboarding_done_at")
