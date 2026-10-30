"""Universitet va grant rasmlari (Mini App sahifalari tepasida)

Rasm bazada saqlanadi (Railway diski har deployda tozalanadi). `cover_version`
har yangi yuklashda oshadi va rasm manziliga qo'shiladi — kesh eskirmaydi.

Revision ID: e1c4a7b9d3f2
Revises: d8b3f1c2e5a7
Create Date: 2026-10-30
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1c4a7b9d3f2"
down_revision: Union[str, None] = "d8b3f1c2e5a7"
branch_labels = None
depends_on = None

TABLES = ("universities", "scholarships")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("cover_data", sa.LargeBinary(), nullable=True))
        op.add_column(table, sa.Column("cover_type", sa.String(length=50), nullable=True))
        op.add_column(
            table,
            sa.Column("cover_version", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "cover_version")
        op.drop_column(table, "cover_type")
        op.drop_column(table, "cover_data")
