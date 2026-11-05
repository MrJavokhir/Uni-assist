"""Grant: bosh sahifa karuselida ko'rsatish

Revision ID: d8b2e5a1c9f3
Revises: c6a1f4d8e2b7
Create Date: 2026-11-04
"""


import sqlalchemy as sa
from alembic import op

revision: str = "d8b2e5a1c9f3"
down_revision: str | None = "c6a1f4d8e2b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scholarships",
        sa.Column("home_featured", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("scholarships", "home_featured")
