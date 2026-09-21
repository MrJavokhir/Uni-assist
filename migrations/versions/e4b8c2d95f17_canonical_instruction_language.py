"""o'qitish tili: "Ingliz tili" -> "English" (programs, scholarships)

Revision ID: e4b8c2d95f17
Revises: d9e3a7c41b28
Create Date: 2026-09-21 17:00:00.000000

O'qitish tili bazada kanonik inglizcha nom bilan saqlanadi (Mini App uni
foydalanuvchi tiliga o'zi o'giradi). Eski sehrgar bo'sh maydonga "Ingliz tili"
yozar edi — shu qiymat "English"ga almashtiriladi.

Kanonik ro'yxatda yo'q boshqa qiymatlar O'ZGARTIRILMAYDI, faqat log'ga
chiqadi: ularni admin qo'lda tuzatadi.

Downgrade faqat shu migratsiya o'zgartirgan qatorlarni asl qiymatiga
qaytaradi — ro'yxat `_language_migration_backup` jadvalida saqlanadi.
"""
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4b8c2d95f17'
down_revision: Union[str, Sequence[str], None] = 'd9e3a7c41b28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = logging.getLogger("alembic.data")

# Migratsiya paytidagi kanonik ro'yxat (ilova konstantasidan import
# QILINMAYDI — keyinchalik ro'yxat o'zgarsa, eski migratsiya o'zgarmasin).
CANONICAL_LANGUAGES = frozenset({
    "English", "Russian", "German", "French", "Korean", "Chinese",
    "Japanese", "Turkish", "Italian", "Polish", "Czech", "Hungarian",
})

# Eski qiymat -> kanonik nom. Kalitlar kichik harfda, chetdagi bo'shliqlarsiz.
LEGACY_LANGUAGE_MAP: dict[str, str] = {
    "ingliz tili": "English",
}

# (jadval, ustun)
TARGETS = [
    ("programs", "language_of_instruction"),
    ("scholarships", "study_language"),
]

BACKUP_TABLE = "_language_migration_backup"


def map_legacy_language(value: str | None) -> str | None:
    """Eski qiymatni kanonik nomga aylantiradi; almashtirish kerak bo'lmasa None."""
    if value is None:
        return None
    return LEGACY_LANGUAGE_MAP.get(value.strip().lower())


def upgrade() -> None:
    """Upgrade schema."""
    backup = op.create_table(
        BACKUP_TABLE,
        sa.Column('table_name', sa.String(length=50), nullable=False),
        sa.Column('row_id', sa.Integer(), nullable=False),
        sa.Column('old_value', sa.String(length=255), nullable=False),
    )
    bind = op.get_bind()
    saved = []

    for table, column in TARGETS:
        rows = bind.execute(
            sa.text(f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL")
        ).fetchall()
        changed = 0
        unknown: dict[str, int] = {}
        for row_id, value in rows:
            canonical = map_legacy_language(value)
            if canonical is not None:
                bind.execute(
                    sa.text(f"UPDATE {table} SET {column} = :v WHERE id = :id"),
                    {"v": canonical, "id": row_id},
                )
                saved.append({"table_name": table, "row_id": row_id, "old_value": value})
                changed += 1
            elif value not in CANONICAL_LANGUAGES:
                unknown[value] = unknown.get(value, 0) + 1

        log.info("%s.%s: %d ta qator kanonik nomga almashtirildi", table, column, changed)
        for value, count in sorted(unknown.items()):
            log.warning(
                "%s.%s: kanonik ro'yxatda yo'q qiymat %r (%d ta qator) - o'zgartirilmadi",
                table, column, value, count,
            )

    if saved:
        op.bulk_insert(backup, saved)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    columns = dict(TARGETS)
    rows = bind.execute(
        sa.text(f"SELECT table_name, row_id, old_value FROM {BACKUP_TABLE}")
    ).fetchall()
    for table, row_id, old_value in rows:
        bind.execute(
            sa.text(f"UPDATE {table} SET {columns[table]} = :v WHERE id = :id"),
            {"v": old_value, "id": row_id},
        )
    op.drop_table(BACKUP_TABLE)
