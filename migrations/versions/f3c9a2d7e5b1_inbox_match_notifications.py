"""Qo'ng'iroqcha (bildirishnomalar) va haftalik "mos dastur" xabarlari

Faqat qo'shadi. Mavjud foydalanuvchilarga `inbox_seen_at = now()` yoziladi:
qo'ng'iroqcha birinchi kuni eski yangiliklar bilan to'lib, hammaga "o'qilmagan"
bo'lib chiqmasin.

Revision ID: f3c9a2d7e5b1
Revises: e1a7c4f9b2d6
Create Date: 2026-11-10
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3c9a2d7e5b1"
down_revision: Union[str, None] = "e1a7c4f9b2d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("inbox_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET inbox_seen_at = now() WHERE inbox_seen_at IS NULL")

    op.create_table(
        "match_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "program_id",
            sa.Integer(),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "program_id", name="uq_match_notification_once"),
    )
    op.create_index("ix_match_notifications_user_id", "match_notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_match_notifications_user_id", table_name="match_notifications")
    op.drop_table("match_notifications")
    op.drop_column("users", "inbox_seen_at")
