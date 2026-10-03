"""Grantlar: ro'yxat tartibi va eskirgan dublikatlarni olib tashlash

IKKI ISH:

1. `sort_order` ustuni. Ro'yxat alifbo tartibida edi va "ADB-Japan" bilan
   boshlanib, o'rtasini 27 ta Erasmus Mundus dasturi egallab turardi —
   Chevening, Fulbright, DAAD kabi eng ko'p qidiriladigan grantlar pastda
   qolardi. Kichik qiymat yuqorida turadi (Field.sort_order bilan bir xil).

2. Eskirgan dublikatlarni o'chirish. Dastlabki yetti yozuv keyinroq ancha
   to'liq, aniq dasturlarga ajratilgan yozuvlar bilan almashtirilgan edi,
   lekin eskilari bazada qolib ketgan. Ular NOMI bo'yicha o'chiriladi (ID
   muhitdan muhitga farq qiladi), shuning uchun bo'sh bazada bu amal hech
   narsa qilmaydi.

   O'chiriladiganlarning hammasi tekshirildi: 18 ta maydondan atigi 5-7 tasi
   to'ldirilgan, birortasida muddat yo'q va birortasi ham dasturga
   bog'lanmagan. O'rnini bosganlarda 9-13 ta maydon va muddat bor.

Revision ID: a7c5e92b14d8
Revises: d8b3e5f21c47
Create Date: 2026-10-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a7c5e92b14d8'
down_revision: Union[str, Sequence[str], None] = 'd8b3e5f21c47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Eski nom -> uning o'rnini bosgan yozuv(lar). Izoh sifatida: nega o'chadi.
SUPERSEDED = {
    "DAAD (Germaniya davlat stipendiyasi)": "DAAD Study Scholarship / Research Grant / EPOS",
    "NAWA (Polsha davlat stipendiyasi)": "Banach Scholarship Programme (NAWA)",
    "Chevening (Buyuk Britaniya)": "Chevening Scholarship",
    "Erasmus Mundus Joint Masters": "27 ta aniq Erasmus Mundus dasturi",
    "Global Korea Scholarship (GKS)": "GKS Undergraduate / Graduate Degrees",
    "Fulbright Foreign Student Program (AQSH)": "Fulbright Foreign Student Program",
    "Türkiye Bursları": "Turkiye Burslari (Turkiye Scholarships)",
}

# Nomi shu bilan BOSHLANADIGAN grantlar yuqoriga chiqadi. O'zbekistonlik
# talabalar orasida eng ko'p so'raladiganlari. Qolganlari 100 da qoladi va
# o'zaro alifbo tartibida ko'rinadi.
PRIORITY = [
    (10, "Chevening Scholarship"),
    (11, "Fulbright Foreign Student Program"),
    (12, "Stipendium Hungaricum"),
    (13, "Turkiye Burslari"),
    (14, "DAAD Study Scholarship"),
    (15, "DAAD Research Grant"),
    (16, "DAAD Development-Related"),
    (17, "Global Korea Scholarship (GKS) - Undergraduate"),
    (18, "Global Korea Scholarship (GKS) - Graduate"),
    (19, "MEXT Scholarship (Japanese Government) - Undergraduate"),
    (20, "MEXT Scholarship (Japanese Government) - Research"),
    (21, "El-Yurt Umidi Foundation Scholarship (Bachelor"),
    (22, "El-Yurt Umidi Foundation Scholarship (Master"),
    (23, "El-Yurt Umidi Foundation Scholarship (PhD"),
    (24, "Global Undergraduate Exchange Program"),
    (25, "Hubert H. Humphrey Fellowship Program"),
    (26, "Banach Scholarship Programme"),
    (27, "Swiss Government Excellence Scholarship"),
    (28, "Italian Government Scholarship"),
    (29, "JDS Japanese Grant Aid Scholarship"),
    # Erasmus Mundus dasturlari ko'p (27 ta) — ular ro'yxat o'rtasini
    # egallab qolmasligi uchun ataylab pastroqqa qo'yiladi.
    (200, "Erasmus Mundus:"),
]


def upgrade() -> None:
    op.add_column(
        "scholarships",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
    )

    bind = op.get_bind()

    # DIQQAT: bu yerda nomlarni chop etib bo'lmaydi. Nomlarda lotin bo'lmagan
    # harflar bor ("Türkiye Bursları" dagi "ı"), Windows konsoli esa cp1252 —
    # `print()` UnicodeEncodeError bilan yiqilib, migratsiyani ham yiqitadi.
    removed = 0
    for old_name in SUPERSEDED:
        result = bind.execute(
            sa.text("delete from scholarships where name = :name"), {"name": old_name}
        )
        removed += result.rowcount or 0
    print(f"  eskirgan dublikatlar: {removed} ta")

    for order, prefix in PRIORITY:
        bind.execute(
            sa.text("update scholarships set sort_order = :o where name like :p"),
            {"o": order, "p": f"{prefix}%"},
        )


def downgrade() -> None:
    # O'chirilgan yozuvlar tiklanmaydi: ular eskirgan va to'liqroq
    # yozuvlar bilan almashtirilgan.
    op.drop_column("scholarships", "sort_order")
