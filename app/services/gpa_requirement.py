"""Dastur talablari matnidan minimal GPA'ni ajratib olish.

Katalogda minimal ball ko'pincha faqat erkin matnda turadi ("min CGPA
2.750/4.00", "minimum GPA 80/100"). Matching esa raqam bilan ishlaydi —
shuning uchun matn import va saqlash paytida shu yerda tahlil qilinadi.

FAQAT MAGISTR VA PhD uchun ishlatiladi: bakalavr talablarida "CGPA 3.00"
odatda foundation/matrikulyatsiya yo'lini bildiradi, foydalanuvchining
o'z bahosi esa maktab bahosi — ularni solishtirish noto'g'ri natija beradi.

Ataylab EHTIYOTKOR: shubhali qator o'tkazib yuboriladi. Noto'g'ri raqam
yozilgandan ko'ra raqam yo'q bo'lgani yaxshi — talab ko'rsatilmagan dastur
matchingda baribir qoladi.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from app.db.models.program import DegreeLevel, GpaScale

DASH = "-–"

# Kirish talabi EMAS bo'lgan qatorlar: bitirish sharti, imtiyoz sharti,
# "minimal ball yo'q" degan izohlar, boshqa shkaladagi baholar.
_EXCLUDE = re.compile(
    r"graduat|\bfinal\s+c?gpa|to complete|waive|no minimum|wide range|exemption"
    r"|german scale|credit hours|\bpoints including|minimum \w+ courses|good standing"
    r"|\bmaintain",
    re.IGNORECASE,
)
# Qavs ichidagi qism odatda SHARTLI qiymat: "CGPA 2.50 (CGPA 2.00 accepted
# with three years' experience)". Asosiy chegara deyarli hech qachon qavsda
# turmaydi, shuning uchun tahlildan oldin olib tashlanadi.
_PARENS = re.compile(r"\([^)]*\)")

# "CGPA 2.75/4.00", "GPA of 3.0 out of 4.0", "CGPA at least 2.75/4.00"
_ON_4 = re.compile(
    r"\bc?gpa\b[^0-9\n]{0,30}?(\d(?:\.\d{1,3})?)\s*(?:/|out of)\s*4(?:\.0+)?\b",
    re.IGNORECASE,
)
# "a GPA of 3.0 to 3.3 out of 4.0" — pastki chegara olinadi.
_RANGE_ON_4 = re.compile(
    r"\bc?gpa\b[^0-9\n]{0,15}?(\d\.\d{1,2})\s*(?:to|[" + DASH + r"])\s*\d\.\d{1,2}"
    r"\s*(?:/|out of)\s*4",
    re.IGNORECASE,
)
# "a GPA of 3.0 or higher" — shkalasi aytilmagan, lekin qiymat <= 4 bo'lsa
# bu AQSH 4.0 shkalasi.
_OR_HIGHER = re.compile(
    r"\bc?gpa\b(?: of)?\s*(\d\.\d{1,2})(?!\d)\s*or\s*(?:higher|above|better)", re.IGNORECASE
)
# Malayziya uslubi: "Bachelor's degree ... with CGPA 2.50" — shkala
# yozilmaydi, lekin CGPA u yerda doim 4.0 shkalada. Faqat kirish talabi
# qatorida ("bachelor"/"degree") va oraliqning boshi bo'lmagan qiymat:
# "CGPA 2.50-2.99 tajriba bilan ko'rib chiqiladi" — bu shartli zona, minimal
# emas.
_CGPA_BARE = re.compile(
    r"\bcgpa\b(?:\s+(?:of|at least|minimum|min\.?|is|from))*\s*"
    r"(\d\.\d{1,3})(?!\d)(?!\s*(?:[" + DASH + r"]|to)\s*\d)(?!\s*(?:/|out of))",
    re.IGNORECASE,
)
_ENTRY = re.compile(r"bachelor|degree", re.IGNORECASE)
# "minimum GPA 80/100"
_ON_100 = re.compile(r"\bc?gpa\b[^0-9\n]{0,15}?(\d{2,3})\s*/\s*100\b", re.IGNORECASE)


@dataclass(frozen=True)
class GpaRequirement:
    value: float
    scale: GpaScale


def extract_gpa_requirement(lines: list[str] | str | None) -> GpaRequirement | None:
    """Matndan eng past (ya'ni kirish uchun yetarli) GPA chegarasini topadi.

    Bir nechta qiymat bo'lsa eng pasti olinadi. Shartli oraliqlar ("2.50-2.99
    tajriba bilan") hisobga kirmaydi — ular naqshlarda chiqarib tashlangan.
    """
    if not lines:
        return None
    if isinstance(lines, str):
        lines = lines.splitlines()

    on_4: list[float] = []
    on_100: list[float] = []
    for line in lines:
        if not line or _EXCLUDE.search(line):
            continue
        line = _PARENS.sub(" ", line)
        for pattern in (_ON_4, _RANGE_ON_4, _OR_HIGHER):
            for match in pattern.finditer(line):
                value = float(match.group(1))
                if 1.0 <= value <= 4.0:
                    on_4.append(value)
        if _ENTRY.search(line):
            for match in _CGPA_BARE.finditer(line):
                value = float(match.group(1))
                if 1.5 <= value <= 4.0:
                    on_4.append(value)
        for match in _ON_100.finditer(line):
            value = float(match.group(1))
            if 40 <= value <= 100:
                on_100.append(value)

    if on_4:
        return GpaRequirement(value=min(on_4), scale=GpaScale.SCALE_4)
    if on_100:
        return GpaRequirement(value=min(on_100), scale=GpaScale.SCALE_100)
    return None


@lru_cache(maxsize=16384)
def _extract_cached(text: str) -> GpaRequirement | None:
    return extract_gpa_requirement(text)


def gpa_requirement_for(program) -> GpaRequirement | None:
    """Dasturning minimal GPA talabi — talablar matnidan hisoblanadi.

    SAQLANMAYDI: admin talablar matnini tahrirlasa, natija o'zi yangilanadi.
    `program_requirements.gpa_min` ustuniga ATAYLAB tayanilmaydi — unda
    adminga ko'rinmaydigan eski seed qiymatlari qolgan.

    Faqat magistr va PhD: bakalavr talabidagi "CGPA 3.00" foundation yo'lini
    bildiradi, foydalanuvchining bahosi esa maktab bahosi.
    """
    if program.degree_level not in (DegreeLevel.MASTER, DegreeLevel.PHD):
        return None
    text = program.requirements_text or ""
    return _extract_cached(text) if text else None
