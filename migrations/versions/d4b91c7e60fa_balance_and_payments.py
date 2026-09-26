"""balans, to'lovlar, to'lov sozlamalari va bot adminlari

Revision ID: d4b91c7e60fa
Revises: c8e41d7b30a5
Create Date: 2026-09-26 17:30:00.000000

Nima qiladi:
  1. `users` ga `balance` (0 dan boshlanadi) va `is_blocked` qo'shadi.
  2. `payment_settings` — karta rekvizitlari va eng kam summa. Bitta qator
     ataylab darhol yaratiladi (id=1), shunda adminka bo'sh ro'yxat emas,
     tahrirlanadigan yozuv ko'rsatadi.
  3. `bot_admins` — botda /approve yoza oladiganlar. BO'SH qoladi: kimning
     Telegram ID si ekanini faqat loyiha egasi biladi, taxmin qilib
     qo'yib bo'lmaydi.
  4. `payments` va `balance_transactions`.

Downgrade hammasini qaytaradi, `users` dagi ikkala ustun ham o'chadi.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b91c7e60fa"
down_revision: Union[str, Sequence[str], None] = "c8e41d7b30a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("balance", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "payment_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_number", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("card_holder", sa.String(length=120), nullable=False, server_default=""),
        sa.Column(
            "min_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="10000",
        ),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="UZS"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    # Adminka bo'sh ro'yxat o'rniga tahrirlanadigan yozuv ko'rsatsin.
    op.execute(
        "INSERT INTO payment_settings (id, card_number, card_holder, min_amount, currency) "
        "VALUES (1, '', '', 10000, 'UZS')"
    )

    op.create_table(
        "bot_admins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="UZS"),
        sa.Column(
            "status",
            sa.Enum(
                "awaiting_receipt",
                "submitted",
                "approved",
                "rejected",
                name="payment_status",
            ),
            nullable=False,
            server_default="awaiting_receipt",
        ),
        sa.Column("receipt_file_id", sa.String(length=255), nullable=True),
        sa.Column("receipt_kind", sa.String(length=20), nullable=True),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_status", "payments", ["status"])

    op.create_table(
        "balance_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("topup", "service", "adjustment", name="transaction_kind"),
            nullable=False,
        ),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("service_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["service_id"], ["admission_services.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_balance_transactions_user_id", "balance_transactions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_balance_transactions_user_id", table_name="balance_transactions")
    op.drop_table("balance_transactions")
    sa.Enum(name="transaction_kind").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")
    sa.Enum(name="payment_status").drop(op.get_bind(), checkfirst=True)

    op.drop_table("bot_admins")
    op.drop_table("payment_settings")

    op.drop_column("users", "is_blocked")
    op.drop_column("users", "balance")
