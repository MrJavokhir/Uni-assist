"""Sovg'a qutisi (gifts, user_gifts) va admin xabarlari (broadcasts)

Faqat qo'shadi: yangi jadvallar va `service_requests.gift_discount` ustuni.

Revision ID: a4d8e1f6c2b9
Revises: f3c9a2d7e5b1
Create Date: 2026-11-10
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4d8e1f6c2b9"
down_revision: Union[str, None] = "f3c9a2d7e5b1"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "gifts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "service_id",
            sa.Integer(),
            sa.ForeignKey("admission_services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("discount_percent", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
    )
    op.create_index("ix_gifts_service_id", "gifts", ["service_id"])

    op.create_table(
        "user_gifts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "gift_id", sa.Integer(), sa.ForeignKey("gifts.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "service_id",
            sa.Integer(),
            sa.ForeignKey("admission_services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column(
            "opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column("service_requests", sa.Column("gift_discount", sa.Integer(), nullable=True))

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
        sa.Column("image_type", sa.String(50), nullable=True),
        sa.Column("button_text", sa.String(64), nullable=True),
        sa.Column("button_kind", sa.String(10), nullable=True),
        sa.Column("button_url", sa.String(500), nullable=True),
        sa.Column("audience", sa.String(10), nullable=False, server_default="all"),
        sa.Column("status", sa.String(20), nullable=False, server_default="sending"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_by", sa.String(100), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )


def downgrade() -> None:
    op.drop_table("broadcasts")
    op.drop_column("service_requests", "gift_discount")
    op.drop_table("user_gifts")
    op.drop_index("ix_gifts_service_id", table_name="gifts")
    op.drop_table("gifts")
