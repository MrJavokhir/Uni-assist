"""Majburiy kanal: obuna oynasidagi rasm

Revision ID: b3e6d9f2a8c4
Revises: a9d4e6b2c7f1
Create Date: 2026-11-04
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3e6d9f2a8c4"
down_revision: Union[str, None] = "a9d4e6b2c7f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("required_channels", sa.Column("logo_url", sa.String(length=500), nullable=True))
    # "Javokhir | Frames" kanali rasmi ilova bilan birga keladi.
    op.execute(
        "UPDATE required_channels SET logo_url = '/webapp/channel-logo.jpg' "
        "WHERE title ILIKE '%frames%'"
    )


def downgrade() -> None:
    op.drop_column("required_channels", "logo_url")
