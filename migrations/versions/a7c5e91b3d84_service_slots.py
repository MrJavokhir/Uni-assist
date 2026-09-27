"""1:1 uchrashuvlar uchun bo'sh vaqtlar

Foydalanuvchi mentor xizmatini buyurtma qilayotganda qaysi kunga
yozilishini o'zi tanlaydi. Vaqtlarni admin kiritadi — mentorning haqiqiy
bandligini bilmasdan avtomatik vaqt taklif qilib bo'lmaydi.

`request_id` UNIQUE: bitta oyna ikki kishiga berilmasligi kerak. Band
qilish `WHERE request_id IS NULL` sharti bilan bajariladi, shuning uchun
ikki odam bir vaqtda bosganda biri yutadi va ikkinchisidan pul
yechilmaydi.

Revision ID: a7c5e91b3d84
Revises: f3b8d24e71a6
Create Date: 2026-09-27
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c5e91b3d84"
down_revision: Union[str, None] = "f3b8d24e71a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admission_services",
        sa.Column("requires_booking", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "service_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("note", sa.String(length=120), nullable=True),
        sa.Column("request_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["service_id"], ["admission_services.id"], ondelete="CASCADE"),
        # So'rov o'chirilsa oyna YO'QOLMAYDI, faqat bo'shaydi.
        sa.ForeignKeyConstraint(["request_id"], ["service_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_service_slots_request_id"),
    )
    op.create_index("ix_service_slots_service_id", "service_slots", ["service_id"])


def downgrade() -> None:
    op.drop_index("ix_service_slots_service_id", table_name="service_slots")
    op.drop_table("service_slots")
    op.drop_column("admission_services", "requires_booking")
