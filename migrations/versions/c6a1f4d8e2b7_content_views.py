"""Dastur va grant sahifalarini ko'rishlar

Revision ID: c6a1f4d8e2b7
Revises: b3e6d9f2a8c4
Create Date: 2026-11-04
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c6a1f4d8e2b7"
down_revision: Union[str, None] = "b3e6d9f2a8c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_views",
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("kind", "target_id", "user_id", "day"),
    )
    op.create_index("ix_content_views_day", "content_views", ["day"])


def downgrade() -> None:
    op.drop_index("ix_content_views_day", table_name="content_views")
    op.drop_table("content_views")
