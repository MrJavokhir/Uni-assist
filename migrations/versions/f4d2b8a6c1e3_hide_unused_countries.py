"""Keraksiz davlatlarni olib tashlash (hukumat grantlariga tegmasdan)

Ro'yxatdagi davlatlar onboarding va admin tanlovlaridan chiqariladi:
- hech narsaga bog'lanmaganlari o'chiriladi;
- hukumat granti yoki universiteti borlari `hidden` qilinadi — grant o'z
  davlati bilan ko'rinishda qoladi, ma'lumot yo'qolmaydi.
Foydalanuvchilarning filtrida tanlangan bo'lsa, u tanlov olib tashlanadi.

Revision ID: f4d2b8a6c1e3
Revises: e1c4a7b9d3f2
Create Date: 2026-10-30
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4d2b8a6c1e3"
down_revision: Union[str, None] = "e1c4a7b9d3f2"
branch_labels = None
depends_on = None

# Bruney, Estoniya, Filippin, Hindiston, JAR, Kolumbiya, Litva, Malta, Pokiston,
# Ruminiya, Serbiya, Kipr, Slovakiya, Sloveniya, Sudan, Tailand, Uganda, Gretsiya.
UNUSED_ISO = (
    "BN",
    "EE",
    "PH",
    "IN",
    "ZA",
    "CO",
    "LT",
    "MT",
    "PK",
    "RO",
    "RS",
    "CY",
    "SK",
    "SI",
    "SD",
    "TH",
    "UG",
    "GR",
)


def upgrade() -> None:
    op.add_column(
        "countries",
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    codes = sa.bindparam("codes", value=list(UNUSED_ISO), expanding=True)
    targets = "SELECT id FROM countries WHERE upper(iso_code) IN :codes"
    op.get_bind().execute(
        sa.text(f"DELETE FROM user_target_country WHERE country_id IN ({targets})").bindparams(
            codes
        )
    )
    op.get_bind().execute(
        sa.text(
            f"""
            DELETE FROM countries
            WHERE id IN ({targets})
              AND NOT EXISTS (SELECT 1 FROM scholarship_country sc WHERE sc.country_id = countries.id)
              AND NOT EXISTS (SELECT 1 FROM universities u WHERE u.country_id = countries.id)
            """
        ).bindparams(codes)
    )
    op.get_bind().execute(
        sa.text(f"UPDATE countries SET hidden = true WHERE id IN ({targets})").bindparams(codes)
    )


def downgrade() -> None:
    # O'chirilgan davlatlar qaytarilmaydi; yashirilganlari yana ko'rinadi.
    op.drop_column("countries", "hidden")
