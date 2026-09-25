""""Ma'lumot noto'g'ri" signallari olib tashlandi

Jadval hech qachon to'lmagan: uni yaratadigan yo'l yo'q edi — na botda, na
Mini App'da "ma'lumot noto'g'ri" tugmasi bor edi, seed ham yozmagan. Faqat
adminkada bo'lim va boshqaruv panelida hisoblagich turardi.

Revision ID: c8e41d7b30a5
Revises: c1f47ab9e082
Create Date: 2026-09-26
"""

import sqlalchemy as sa
from alembic import op

revision = "c8e41d7b30a5"
down_revision = "c1f47ab9e082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("reports")
    # Native enum turi jadval bilan birga o'chmaydi — alohida tushiriladi.
    sa.Enum(name="report_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=True),
        sa.Column("scholarship_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("new", "reviewed", "resolved", name="report_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
