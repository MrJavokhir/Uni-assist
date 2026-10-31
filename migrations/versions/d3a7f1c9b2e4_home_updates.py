"""Mini App bosh sahifasidagi "Yangiliklar" (admin panelda yoziladi)

Revision ID: d3a7f1c9b2e4
Revises: c8f2a4d6e1b9
Create Date: 2026-10-31
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d3a7f1c9b2e4"
down_revision: Union[str, None] = "c8f2a4d6e1b9"
branch_labels = None
depends_on = None

KINDS = ("new", "open", "deadline", "info")


def upgrade() -> None:
    kind = postgresql.ENUM(*KINDS, name="update_kind")
    kind.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "home_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("title_ru", sa.String(length=200), nullable=True),
        sa.Column("title_en", sa.String(length=200), nullable=True),
        sa.Column(
            "kind",
            postgresql.ENUM(*KINDS, name="update_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("published_on", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column(
            "scholarship_id",
            sa.Integer(),
            sa.ForeignKey("scholarships.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("home_updates")
    postgresql.ENUM(name="update_kind").drop(op.get_bind(), checkfirst=True)
