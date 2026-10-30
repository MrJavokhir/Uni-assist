"""Universitet/grant rasmi: yuklash o'rniga havola (logotip kabi)

Avval yuklangan rasmlar yo'qolmaydi: ularning manzili (/api/webapp/images/...)
yangi `cover_url` ustuniga yoziladi, baytlar esa `cover_data`da qoladi.

Revision ID: a7e3c9d1b4f8
Revises: f4d2b8a6c1e3
Create Date: 2026-10-30
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7e3c9d1b4f8"
down_revision: Union[str, None] = "f4d2b8a6c1e3"
branch_labels = None
depends_on = None

TABLES = {"universities": "university", "scholarships": "scholarship"}


def upgrade() -> None:
    for table, kind in TABLES.items():
        op.add_column(table, sa.Column("cover_url", sa.String(length=500), nullable=True))
        op.execute(
            f"""
            UPDATE {table}
            SET cover_url = '/api/webapp/images/{kind}/' || id || '?v=' || cover_version
            WHERE cover_data IS NOT NULL AND cover_version > 0
            """
        )
        op.drop_column(table, "cover_version")


def downgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("cover_version", sa.Integer(), nullable=False, server_default="0"),
        )
        op.execute(f"UPDATE {table} SET cover_version = 1 WHERE cover_data IS NOT NULL")
        op.drop_column(table, "cover_url")
