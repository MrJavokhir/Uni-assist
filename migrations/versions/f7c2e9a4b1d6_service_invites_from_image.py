"""Admission Kit: takliflar sanalish sanasi va rasm havolasi

Mavjud xizmatlarda `invites_count_from` bo'sh qoladi — ularda yig'ilgan
takliflar hisobi saqlanadi. Yangi xizmatlarga yaratilgan vaqti qo'yiladi
(server_default), ya'ni eski takliflar yangi qo'llanmani ochmaydi.

Revision ID: f7c2e9a4b1d6
Revises: e5b9c3a1d7f2
Create Date: 2026-11-03
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7c2e9a4b1d6"
down_revision: Union[str, None] = "e5b9c3a1d7f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Avval default'siz qo'shiladi (mavjud qatorlar NULL), keyin default beriladi.
    op.add_column(
        "admission_services",
        sa.Column("invites_count_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("admission_services", "invites_count_from", server_default=sa.func.now())
    op.add_column(
        "admission_services", sa.Column("image_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("admission_services", "image_url")
    op.drop_column("admission_services", "invites_count_from")
