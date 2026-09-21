"""fields: yo'nalishlar ma'lumotnomasi; programs/users -> field_id

Revision ID: d9e3a7c41b28
Revises: c8d4f1a2e657
Create Date: 2026-09-21 16:00:00.000000

Nima qiladi:
  1. `fields` jadvalini yaratib, 18 ta kanonik yo'nalishni kiritadi.
  2. `programs.field_id` va `users.field_id` (FK, ON DELETE SET NULL) qo'shadi.
  3. Eski erkin matnni (`programs.field_of_study`, `users.major`) ma'lumotnomaga
     ko'chiradi. Mos kelmagan qiymat uchun field_id NULL qoladi va qiymat
     log'ga chiqadi — prod bazaga tashqaridan ulanib bo'lmaydi, shuning uchun
     migratsiya noma'lum qiymatda YIQILMAYDI.
  4. Eski ustunlarni `*_legacy` deb qayta nomlaydi (o'chirmaydi): admin
     "Yo'nalishi yo'q" dasturning eski qiymatini ko'rib, to'g'ri yo'nalishni
     tanlaydi. Downgrade shu tufayli ma'lumot yo'qotmaydi.
"""
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e3a7c41b28'
down_revision: Union[str, Sequence[str], None] = 'c8d4f1a2e657'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = logging.getLogger("alembic.data")

# (code, name_uz, name_ru, name_en) — tartib sort_order bo'ladi.
FIELDS: list[tuple[str, str, str, str]] = [
    ("cs_it", "Kompyuter fanlari va IT",
     "Компьютерные науки и ИТ", "Computer Science & IT"),
    ("business_mgmt", "Biznes va menejment",
     "Бизнес и менеджмент", "Business & Management"),
    ("economics_finance", "Iqtisodiyot va moliya",
     "Экономика и финансы", "Economics & Finance"),
    ("engineering", "Muhandislik",
     "Инженерия", "Engineering"),
    ("medicine_health", "Tibbiyot va sog'liqni saqlash",
     "Медицина и здравоохранение", "Medicine & Health"),
    ("intl_relations", "Xalqaro munosabatlar va davlat boshqaruvi",
     "Международные отношения и государственное управление",
     "International Relations & Public Policy"),
    ("education_ling", "Ta'lim va tilshunoslik",
     "Образование и лингвистика", "Education & Linguistics"),
    ("law", "Huquqshunoslik",
     "Юриспруденция", "Law"),
    ("energy", "Energetika",
     "Энергетика", "Energy & Power Engineering"),
    ("arch_construction", "Arxitektura va qurilish",
     "Архитектура и строительство", "Architecture & Construction"),
    ("transport_logistics", "Transport va logistika",
     "Транспорт и логистика", "Transport & Logistics"),
    ("natural_sciences", "Tabiiy fanlar",
     "Естественные науки", "Natural Sciences"),
    ("agri_water", "Qishloq va suv xo'jaligi",
     "Сельское и водное хозяйство", "Agriculture & Water Management"),
    ("media_comm", "Media va kommunikatsiya",
     "Медиа и коммуникации", "Media & Communication"),
    ("psychology_social", "Psixologiya va ijtimoiy fanlar",
     "Психология и социальные науки", "Psychology & Social Sciences"),
    ("geodesy_mining", "Geodeziya, geologiya va konchilik",
     "Геодезия, геология и горное дело", "Geodesy, Geology & Mining"),
    ("arts_design", "San'at va dizayn",
     "Искусство и дизайн", "Arts & Design"),
    ("tourism_hospitality", "Turizm va mehmonxona ishi",
     "Туризм и гостиничное дело", "Tourism & Hospitality"),
]

# Eski erkin matn -> yo'nalish kodi. Kalitlar kichik harfda, chetdagi
# bo'shliqlarsiz (qarang: `map_legacy_field`).
LEGACY_FIELD_MAP: dict[str, str] = {
    "computer science": "cs_it",
    "engineering": "engineering",
    "business / economics": "business_mgmt",
    "law": "law",
}


def map_legacy_field(value: str | None) -> str | None:
    """Eski yo'nalish matnini kodga aylantiradi; mos kelmasa None.

    Registrga sezgir emas, chetdagi bo'shliqlar qirqiladi.
    """
    if value is None:
        return None
    return LEGACY_FIELD_MAP.get(value.strip().lower())


def _migrate_column(bind, table: str, column: str, field_ids: dict[str, int]) -> None:
    rows = bind.execute(
        sa.text(f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL")
    ).fetchall()
    unknown: dict[str, int] = {}
    mapped = 0
    for row_id, value in rows:
        code = map_legacy_field(value)
        if code is None:
            if value.strip():
                unknown[value] = unknown.get(value, 0) + 1
            continue
        bind.execute(
            sa.text(f"UPDATE {table} SET field_id = :fid WHERE id = :id"),
            {"fid": field_ids[code], "id": row_id},
        )
        mapped += 1

    log.info("%s.%s: %d ta qator yo'nalishga biriktirildi", table, column, mapped)
    for value, count in sorted(unknown.items()):
        log.warning(
            "%s.%s: noma'lum qiymat %r (%d ta qator) - field_id NULL qoldi",
            table, column, value, count,
        )


def upgrade() -> None:
    """Upgrade schema."""
    fields = op.create_table(
        'fields',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('name_uz', sa.String(length=150), nullable=False),
        sa.Column('name_ru', sa.String(length=150), nullable=False),
        sa.Column('name_en', sa.String(length=150), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.bulk_insert(
        fields,
        [
            {"code": code, "name_uz": uz, "name_ru": ru, "name_en": en, "sort_order": i * 10}
            for i, (code, uz, ru, en) in enumerate(FIELDS, start=1)
        ],
    )

    op.add_column('programs', sa.Column('field_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'programs_field_id_fkey', 'programs', 'fields', ['field_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_programs_field_id', 'programs', ['field_id'])

    op.add_column('users', sa.Column('field_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'users_field_id_fkey', 'users', 'fields', ['field_id'], ['id'], ondelete='SET NULL',
    )

    bind = op.get_bind()
    field_ids = dict(bind.execute(sa.text("SELECT code, id FROM fields")).fetchall())
    _migrate_column(bind, "programs", "field_of_study", field_ids)
    _migrate_column(bind, "users", "major", field_ids)

    op.alter_column('programs', 'field_of_study',
                    new_column_name='field_of_study_legacy', nullable=True)
    op.alter_column('users', 'major', new_column_name='major_legacy')


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    # Upgrade'dan keyin yaratilgan dasturlarda eski matn yo'q — NOT NULL
    # cheklovini qaytarishdan oldin yo'nalish nomi (inglizcha) bilan to'ldiriladi.
    bind.execute(sa.text(
        "UPDATE programs p SET field_of_study_legacy = f.name_en "
        "FROM fields f WHERE p.field_id = f.id AND p.field_of_study_legacy IS NULL"
    ))
    bind.execute(sa.text(
        "UPDATE programs SET field_of_study_legacy = '—' WHERE field_of_study_legacy IS NULL"
    ))
    bind.execute(sa.text(
        "UPDATE users u SET major_legacy = f.name_en "
        "FROM fields f WHERE u.field_id = f.id AND u.major_legacy IS NULL"
    ))

    op.alter_column('users', 'major_legacy', new_column_name='major')
    op.alter_column('programs', 'field_of_study_legacy',
                    new_column_name='field_of_study', nullable=False)

    op.drop_constraint('users_field_id_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'field_id')
    op.drop_index('ix_programs_field_id', table_name='programs')
    op.drop_constraint('programs_field_id_fkey', 'programs', type_='foreignkey')
    op.drop_column('programs', 'field_id')
    op.drop_table('fields')
