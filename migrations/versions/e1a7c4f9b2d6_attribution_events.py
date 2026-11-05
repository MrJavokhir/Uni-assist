"""Deep link atributsiyasi, hodisalar, kampaniya havolalari va xarajatlari

Faqat qo'shadi — hech qanday ma'lumot o'chirilmaydi. Mavjud foydalanuvchilar
`first_source = 'legacy'`, `first_seen_at = created_at` oladi.

Revision ID: e1a7c4f9b2d6
Revises: d8b2e5a1c9f3
Create Date: 2026-11-05
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1a7c4f9b2d6"
down_revision: Union[str, None] = "d8b2e5a1c9f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_source", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("first_param_raw", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_source", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("pending_target", postgresql.JSONB(), nullable=True))
    op.add_column(
        "users", sa.Column("pending_target_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_users_first_source", "users", ["first_source"])
    op.create_index("ix_users_first_seen_at", "users", ["first_seen_at"])
    op.execute(
        "UPDATE users SET first_source = 'legacy', first_seen_at = created_at "
        "WHERE first_seen_at IS NULL"
    )

    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("source", sa.String(32), nullable=True),
        sa.Column("props", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_events_user_created", "events", ["user_id", "created_at"])
    op.create_index("ix_events_name_created", "events", ["name", "created_at"])
    op.create_index(
        "uq_events_once",
        "events",
        ["user_id", "name"],
        unique=True,
        postgresql_where=sa.text("name IN ('gate_passed', 'filter_completed', 'first_save')"),
    )

    op.create_table(
        "campaign_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prefix", sa.String(8), nullable=False),
        sa.Column("campaign", sa.String(64), nullable=False),
        sa.Column("variant", sa.String(8), nullable=True),
        sa.Column("param", sa.String(64), nullable=False, unique=True),
        sa.Column("target", postgresql.JSONB(), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_campaign_links_prefix_campaign", "campaign_links", ["prefix", "campaign"]
    )

    op.create_table(
        "campaign_costs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_or_campaign", sa.String(64), nullable=False),
        sa.Column("spend", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("rate_to_usd", sa.Numeric(18, 8), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_campaign_costs_source_or_campaign", "campaign_costs", ["source_or_campaign"]
    )


def downgrade() -> None:
    op.drop_table("campaign_costs")
    op.drop_table("campaign_links")
    op.drop_table("events")
    op.drop_index("ix_users_first_seen_at", table_name="users")
    op.drop_index("ix_users_first_source", table_name="users")
    for column in (
        "pending_target_expires_at",
        "pending_target",
        "last_source",
        "first_seen_at",
        "first_param_raw",
        "first_source",
    ):
        op.drop_column("users", column)
