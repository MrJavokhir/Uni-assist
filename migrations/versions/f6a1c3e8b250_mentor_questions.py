"""Mentordan so'rash: savollar, yozishma, shikoyatlar, davlat topic'lari

Qo'shiladi:
  country_topics     — davlat -> mentorlar guruhidagi topic
  mentor_questions   — savollar (+ ommaviy raqam uchun alohida sequence)
  mentor_messages    — yozishma tarixi
  mentor_complaints  — foydalanuvchi shikoyatlari

Mentorlar jadvali YO'Q: guruh a'zoligining o'zi mentorlik huquqi.

Revision ID: f6a1c3e8b250
Revises: b2f9d41a6c83
Create Date: 2026-10-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a1c3e8b250"
down_revision: Union[str, Sequence[str], None] = "b2f9d41a6c83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENUMS = {
    "mentor_level": ("bachelor", "master"),
    "mentor_topic": ("admission", "documents", "visa", "living", "work", "studies", "other"),
    "mentor_question_status": ("open", "claimed", "answered", "closed"),
    "mentor_sender": ("user", "mentor"),
    "mentor_complaint_reason": ("wrong_info", "disrespect", "paid_or_ad", "other"),
    "mentor_complaint_status": ("new", "reviewed"),
}


def _enum(name: str) -> sa.Enum:
    return sa.Enum(*_ENUMS[name], name=name)


def upgrade() -> None:
    op.create_table(
        "country_topics",
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("message_thread_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("country_code"),
    )

    op.execute("CREATE SEQUENCE mentor_question_number_seq START WITH 100")
    op.create_table(
        "mentor_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "public_number",
            sa.Integer(),
            server_default=sa.text("nextval('mentor_question_number_seq')"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("level", _enum("mentor_level"), nullable=False),
        sa.Column("topic", _enum("mentor_topic"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "status", _enum("mentor_question_status"), server_default="open", nullable=False
        ),
        sa.Column("claimed_by_tg_id", sa.BigInteger(), nullable=True),
        sa.Column("claimed_by_name", sa.String(length=255), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("group_message_id", sa.BigInteger(), nullable=True),
        sa.Column("force_reply_message_id", sa.BigInteger(), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_24h_sent", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("user_notified_48h", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("admin_notified", sa.Boolean(), server_default="false", nullable=False),
        sa.CheckConstraint("rating is null or rating between 1 and 5", name="ck_mentor_rating"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_number"),
    )
    # Sequence jadval bilan birga o'chsin (DROP TABLE uni ham olib ketadi).
    op.execute("ALTER SEQUENCE mentor_question_number_seq OWNED BY mentor_questions.public_number")
    op.create_index(
        "ix_mentor_questions_user_created", "mentor_questions", ["user_id", "created_at"]
    )
    op.create_index("ix_mentor_questions_status", "mentor_questions", ["status"])

    op.create_table(
        "mentor_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("sender", _enum("mentor_sender"), nullable=False),
        sa.Column("mentor_tg_id", sa.BigInteger(), nullable=True),
        sa.Column("mentor_name", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["question_id"], ["mentor_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mentor_messages_question", "mentor_messages", ["question_id"])

    op.create_table(
        "mentor_complaints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reason", _enum("mentor_complaint_reason"), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "status", _enum("mentor_complaint_status"), server_default="new", nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["question_id"], ["mentor_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["mentor_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("mentor_complaints")
    op.drop_index("ix_mentor_messages_question", table_name="mentor_messages")
    op.drop_table("mentor_messages")
    op.drop_index("ix_mentor_questions_status", table_name="mentor_questions")
    op.drop_index("ix_mentor_questions_user_created", table_name="mentor_questions")
    op.drop_table("mentor_questions")
    op.execute("DROP SEQUENCE IF EXISTS mentor_question_number_seq")
    op.drop_table("country_topics")
    for name in reversed(list(_ENUMS)):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
