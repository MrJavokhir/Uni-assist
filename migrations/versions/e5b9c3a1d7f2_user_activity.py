"""Foydalanuvchi faolligi: oxirgi kirish vaqti va faol kunlar jurnali

Eski foydalanuvchilarda `last_seen_at` bo'sh — ular keyingi kirishida
belgilanadi (avvalgi faollik hech qayerda yozilmagan edi).

Revision ID: e5b9c3a1d7f2
Revises: d3a7f1c9b2e4
Create Date: 2026-11-01
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5b9c3a1d7f2"
down_revision: Union[str, None] = "d3a7f1c9b2e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_last_seen_at", "users", ["last_seen_at"])
    op.create_table(
        "user_activity_days",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("day", sa.Date(), primary_key=True),
    )
    op.create_index("ix_user_activity_days_day", "user_activity_days", ["day"])


def downgrade() -> None:
    op.drop_table("user_activity_days")
    op.drop_index("ix_users_last_seen_at", table_name="users")
    op.drop_column("users", "last_seen_at")
