"""Admission Kit xizmatlariga PDF fayl biriktirish

Fayl baytlari BAZADA saqlanadi, diskda emas: prod Railway'da ishlaydi va
konteyner fayl tizimi har deployda toza holga qaytadi — diskka yozilgan PDF
birinchi yangilanishda yo'qolardi.

Baytlar `admission_services` ichida emas, alohida jadvalda: xizmatlar
ro'yxati ilova har ochilganda o'qiladi, baytlar esa o'sha satrda tursa har
so'rovda behuda tortilardi.

Revision ID: e6a2c81d5f94
Revises: d4b91c7e60fa
Create Date: 2026-09-27
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6a2c81d5f94"
down_revision: Union[str, None] = "d4b91c7e60fa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=200), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("telegram_file_id", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["service_id"], ["admission_services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Bitta xizmatga bitta fayl: yangisi yuklansa eskisi O'RNIGA yoziladi,
        # shuning uchun "qaysi biri joriy" degan savol tug'ilmaydi.
        sa.UniqueConstraint("service_id", name="uq_service_files_service_id"),
    )


def downgrade() -> None:
    op.drop_table("service_files")
