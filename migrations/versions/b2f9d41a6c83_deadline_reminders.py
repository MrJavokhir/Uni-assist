"""Deadline eslatmalari: oy darajasidagi muddat, xabarlar jurnali, takliflar

Qo'shiladi:
  programs.deadline_month        — aniq sana ma'lum bo'lmaganda, odatdagi oy
  users.notifications_enabled    — eslatmalarning umumiy sozlamasi
  users.notifications_enabled_at — oxirgi marta yoqilgan payt
  notification_logs              — yuborilgan xabarlar (dublikat nazorati + statistika)
  deadline_suggestions           — foydalanuvchi taklif qilgan sanalar

NEGA `programs` ga SANA QO'SHILMAYDI: aniq sanalar allaqachon `deadlines`
jadvalida saqlanadi. Sanani `programs` ga ham yozish ikkinchi manba yaratardi
va ular zid bo'lganda qaysi biri to'g'ri ekani noaniq qolardi. Deadline turi
(exact / month / unknown) hisoblab chiqariladi, saqlanmaydi — shuning uchun
ular bir-biridan uzilib qolishi mumkin emas.

Revision ID: b2f9d41a6c83
Revises: e5c1b47d920f
Create Date: 2026-10-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b2f9d41a6c83'
down_revision: Union[str, Sequence[str], None] = 'e5c1b47d920f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("programs", sa.Column("deadline_month", sa.Integer(), nullable=True))
    # Oy faqat 1-12 bo'lishi mumkin. Tekshiruv bazada: admin paneli ham, API
    # ham, kelajakdagi import skriptlari ham shu chegaradan o'tolmaydi.
    op.create_check_constraint(
        "ck_programs_deadline_month",
        "programs",
        "deadline_month is null or (deadline_month between 1 and 12)",
    )

    op.add_column(
        "users",
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("notifications_enabled_at", sa.DateTime(timezone=True), nullable=True),
    )

    notification_type = sa.Enum(
        "exact_14d",
        "exact_3d",
        "exact_immediate",
        "month_before",
        "month_start",
        "unknown_check",
        name="notification_type",
    )
    suggestion_status = sa.Enum("pending", "approved", "rejected", name="suggestion_status")

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("notif_type", notification_type, nullable=False),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("clicked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Bir xil xabar ikki marta ketmasligining KAFOLATI shu yerda, kodda
        # emas: ikkita scheduler bir vaqtda ishga tushsa ham baza ruxsat bermaydi.
        sa.UniqueConstraint("user_id", "program_id", "notif_type", name="uq_notification_once"),
    )
    op.create_index("ix_notification_logs_user_id", "notification_logs", ["user_id"])
    op.create_index("ix_notification_logs_program_id", "notification_logs", ["program_id"])
    op.create_index("ix_notification_logs_sent_at", "notification_logs", ["sent_at"])

    op.create_table(
        "deadline_suggestions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("suggested_date", sa.Date(), nullable=False),
        sa.Column(
            "status", suggestion_status, server_default=sa.text("'pending'"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deadline_suggestions_user_id", "deadline_suggestions", ["user_id"])
    op.create_index("ix_deadline_suggestions_program_id", "deadline_suggestions", ["program_id"])
    op.create_index("ix_deadline_suggestions_status", "deadline_suggestions", ["status"])
    # Bitta odam bitta dastur uchun faqat BITTA kutilayotgan taklif bera oladi.
    # Qisman indeks: tasdiqlangan/rad etilganlar cheklanmaydi.
    op.create_index(
        "uq_one_pending_suggestion",
        "deadline_suggestions",
        ["user_id", "program_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_table("deadline_suggestions")
    op.drop_table("notification_logs")
    sa.Enum(name="suggestion_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notification_type").drop(op.get_bind(), checkfirst=True)

    op.drop_column("users", "notifications_enabled_at")
    op.drop_column("users", "notifications_enabled")

    op.drop_constraint("ck_programs_deadline_month", "programs", type_="check")
    op.drop_column("programs", "deadline_month")
