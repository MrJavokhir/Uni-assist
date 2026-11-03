"""Admission Kit: admin panelda yuklanadigan xizmat ikonkasi

Revision ID: a9d4e6b2c7f1
Revises: f7c2e9a4b1d6
Create Date: 2026-11-03
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9d4e6b2c7f1"
down_revision: Union[str, None] = "f7c2e9a4b1d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("admission_services", sa.Column("icon_data", sa.LargeBinary(), nullable=True))
    op.add_column("admission_services", sa.Column("icon_type", sa.String(length=50), nullable=True))
    op.add_column(
        "admission_services",
        sa.Column("icon_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("admission_services", "icon_version")
    op.drop_column("admission_services", "icon_type")
    op.drop_column("admission_services", "icon_data")
