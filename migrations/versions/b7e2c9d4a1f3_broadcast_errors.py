"""Xabar yuborish: sinov xatosi va oxirgi xato sababi

Faqat qo'shadi: `broadcasts.test_error`, `broadcasts.last_error`.

Revision ID: b7e2c9d4a1f3
Revises: a4d8e1f6c2b9
Create Date: 2026-11-10
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2c9d4a1f3"
down_revision: Union[str, None] = "a4d8e1f6c2b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("broadcasts", sa.Column("test_error", sa.Text(), nullable=True))
    op.add_column("broadcasts", sa.Column("last_error", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("broadcasts", "last_error")
    op.drop_column("broadcasts", "test_error")
