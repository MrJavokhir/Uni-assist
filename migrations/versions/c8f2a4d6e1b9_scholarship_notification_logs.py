"""Hukumat granti muddati eslatmalari jurnali (30 kun qolganda)

Revision ID: c8f2a4d6e1b9
Revises: b5d1e8f3a2c6
Create Date: 2026-10-31
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8f2a4d6e1b9"
down_revision: Union[str, None] = "b5d1e8f3a2c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scholarship_notification_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "scholarship_id",
            sa.Integer(),
            sa.ForeignKey("scholarships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("deadline_date", sa.Date(), nullable=False),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "user_id", "scholarship_id", "deadline_date", name="uq_scholarship_notification_once"
        ),
    )
    op.create_index(
        "ix_scholarship_notification_logs_user_id", "scholarship_notification_logs", ["user_id"]
    )
    op.create_index(
        "ix_scholarship_notification_logs_scholarship_id",
        "scholarship_notification_logs",
        ["scholarship_id"],
    )


def downgrade() -> None:
    op.drop_table("scholarship_notification_logs")
