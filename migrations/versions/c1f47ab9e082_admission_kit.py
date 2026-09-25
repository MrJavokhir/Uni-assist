"""admission_services va service_requests jadvallari (Admission Kit)

Revision ID: c1f47ab9e082
Revises: b7c2e58a04d3
Create Date: 2026-09-25 23:30:00.000000

Nima qiladi:
  1. `admission_services` — pullik xizmatlar katalogi (matnlar uch tilda,
     narx, tartib, faollik). Katalog kodda emas, adminkada boshqariladi.
  2. `service_requests` — foydalanuvchining xizmatga qiziqishi. To'lov emas:
     admin ro'yxatni ko'rib o'zi bog'lanadi.
  3. To'rtta boshlang'ich xizmatni kiritadi — sahifa bo'sh ochilmasin.
     Matn va narxlar keyin adminkadan tahrirlanadi, shuning uchun narx
     ataylab NULL ("Narx kelishiladi" deb chiqadi).

Downgrade ikkala jadvalni ham o'chiradi.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1f47ab9e082"
down_revision: Union[str, Sequence[str], None] = "b7c2e58a04d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (code, title_uz, title_ru, title_en, desc_uz, desc_ru, desc_en)
SERVICES: list[tuple[str, str, str, str, str, str, str]] = [
    (
        "motivation_letter",
        "Motivatsion xat bo'yicha qo'llanma",
        "Руководство по мотивационному письму",
        "Motivation letter guide",
        (
            "Kuchli motivatsion xat tuzilishi, bosqichma-bosqich namunalar va "
            "eng ko'p uchraydigan xatolar ro'yxati."
        ),
        (
            "Структура сильного мотивационного письма, пошаговые примеры и "
            "список самых частых ошибок."
        ),
        (
            "The structure of a strong motivation letter, step-by-step examples "
            "and a list of the most common mistakes."
        ),
    ),
    (
        "cv_guide",
        "CV yozish bo'yicha qo'llanma",
        "Руководство по составлению CV",
        "CV writing guide",
        (
            "Xalqaro universitetlar kutadigan akademik CV shakli, bo'limlar "
            "ketma-ketligi va tayyor andoza."
        ),
        (
            "Формат академического CV, который ждут зарубежные университеты, "
            "порядок разделов и готовый шаблон."
        ),
        (
            "The academic CV format international universities expect, the order "
            "of sections and a ready-made template."
        ),
    ),
    (
        "mentor_1on1",
        "Mentor bilan 1:1 maslahat",
        "Консультация с ментором 1:1",
        "1-on-1 mentor session",
        (
            "Chet elda o'qigan mentor bilan shaxsiy uchrashuv: universitet "
            "tanlash, hujjatlar va ariza strategiyasi."
        ),
        (
            "Личная встреча с ментором, который учился за рубежом: выбор "
            "университета, документы и стратегия подачи."
        ),
        (
            "A personal session with a mentor who studied abroad: choosing a "
            "university, documents and application strategy."
        ),
    ),
    (
        "full_application",
        "Arizada to'liq yordam",
        "Полное сопровождение заявки",
        "Full application support",
        (
            "Universitet tanlashdan hujjat topshirishgacha boshidan oxirigacha "
            "birga olib boramiz."
        ),
        (
            "Ведём от выбора университета до подачи документов — от начала до "
            "конца вместе."
        ),
        (
            "We guide you from choosing a university to submitting the "
            "documents, end to end."
        ),
    ),
]


def upgrade() -> None:
    op.create_table(
        "admission_services",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("title_uz", sa.String(length=150), nullable=False),
        sa.Column("title_ru", sa.String(length=150), nullable=True),
        sa.Column("title_en", sa.String(length=150), nullable=True),
        sa.Column("description_uz", sa.Text(), nullable=True),
        sa.Column("description_ru", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("price_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("price_currency", sa.String(length=10), nullable=False, server_default="UZS"),
        sa.Column("price_note_uz", sa.String(length=60), nullable=True),
        sa.Column("price_note_ru", sa.String(length=60), nullable=True),
        sa.Column("price_note_en", sa.String(length=60), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # Enum turini ATAYLAB oldindan yaratmaymiz: `create_table` uni o'zi
    # yaratadi. Ikkalasini birga qilsak, `CREATE TYPE` ikki marta yuborilib
    # "type already exists" bilan yiqiladi (loyihadagi boshqa migratsiyalar
    # ham shu uslubda — 8d2aabaf3840_initial_schema.py).
    op.create_table(
        "service_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("new", "contacted", "done", "cancelled", name="service_request_status"),
            nullable=False,
            server_default="new",
        ),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["service_id"], ["admission_services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_requests_service_id", "service_requests", ["service_id"])
    op.create_index("ix_service_requests_user_id", "service_requests", ["user_id"])

    services = sa.table(
        "admission_services",
        sa.column("code", sa.String),
        sa.column("title_uz", sa.String),
        sa.column("title_ru", sa.String),
        sa.column("title_en", sa.String),
        sa.column("description_uz", sa.Text),
        sa.column("description_ru", sa.Text),
        sa.column("description_en", sa.Text),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        services,
        [
            {
                "code": code,
                "title_uz": t_uz,
                "title_ru": t_ru,
                "title_en": t_en,
                "description_uz": d_uz,
                "description_ru": d_ru,
                "description_en": d_en,
                "sort_order": index,
            }
            for index, (code, t_uz, t_ru, t_en, d_uz, d_ru, d_en) in enumerate(SERVICES)
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_service_requests_user_id", table_name="service_requests")
    op.drop_index("ix_service_requests_service_id", table_name="service_requests")
    op.drop_table("service_requests")
    sa.Enum(name="service_request_status").drop(op.get_bind(), checkfirst=True)
    op.drop_table("admission_services")
