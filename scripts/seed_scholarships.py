"""Davlat stipendiyalarini bazaga kiritadi (DAAD, Chevening, Erasmus Mundus...).

Idempotent: grant nomi bo'yicha upsert qilinadi, shuning uchun skriptni bir necha
marta ishga tushirsa ham dublikat yaratmaydi. Grant tegishli bo'lgan davlatlar
ham ISO kodi bo'yicha topiladi/yaratiladi.

MUHIM: stipend_amount ataylab bo'sh (None) qoldirilgan — bu summalar yiliga
o'zgaradi va rasmiy saytdan tasdiqlanishi kerak. Har bir grant tavsifida
"TODO: rasmiy saytdan tasdiqlash kerak" izohi bor, admin panelda to'ldiriladi.

Ishlatish:
    uv run python scripts/seed_scholarships.py
"""

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# Skript `python scripts/...` bilan ishga tushirilganda sys.path[0] — scripts/
# papkasi bo'ladi, shuning uchun loyiha ildizini qo'lda qo'shamiz.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Country, CoverageType, Scholarship, UniversityChoiceType
from app.db.session import async_session_factory

VERIFIED_BY = "seed"
TODO_NOTE = "TODO: aniq summa va joriy talablarni rasmiy saytdan tasdiqlash kerak."


@dataclass
class CountrySeed:
    iso_code: str
    name_uz: str
    name_ru: str
    name_en: str


@dataclass
class ScholarshipSeed:
    name: str
    country_iso: list[str]
    coverage_type: CoverageType
    university_choice: UniversityChoiceType
    source_url: str
    description: str
    currency: str = "USD"
    coverage_percent: int | None = None
    extras_flight: bool = False
    extras_insurance: bool = False
    extras_dormitory: bool = False
    extras_language_course: bool = False
    application_linked_to_program: bool = False
    age_limit: int | None = None
    programs_note: str = field(default="", repr=False)


# Grantlar tegishli bo'lgan davlatlar (agar bazada bo'lmasa, yaratiladi).
COUNTRIES: list[CountrySeed] = [
    CountrySeed("DE", "Germaniya", "Германия", "Germany"),
    CountrySeed("HU", "Vengriya", "Венгрия", "Hungary"),
    CountrySeed("PL", "Polsha", "Польша", "Poland"),
    CountrySeed("GB", "Buyuk Britaniya", "Великобритания", "United Kingdom"),
    CountrySeed("KR", "Janubiy Koreya", "Южная Корея", "South Korea"),
    CountrySeed("US", "AQSH", "США", "United States"),
    CountrySeed("TR", "Turkiya", "Турция", "Turkey"),
]

SCHOLARSHIPS: list[ScholarshipSeed] = [
    ScholarshipSeed(
        name="DAAD (Germaniya davlat stipendiyasi)",
        country_iso=["DE"],
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        source_url="https://www.daad.de/en/study-and-research-in-germany/scholarships/",
        currency="EUR",
        extras_insurance=True,
        extras_flight=True,
        extras_language_course=True,
        description=(
            "Germaniya akademik almashinuv xizmati (DAAD) stipendiyasi. Magistratura va "
            "PhD uchun oylik stipendiya, sog'liq sug'urtasi, ko'p hollarda aviachipta va "
            "til kursi qoplanadi. Universitetni talabaning o'zi tanlaydi.\n"
            f"{TODO_NOTE}"
        ),
    ),
    ScholarshipSeed(
        name="Stipendium Hungaricum",
        country_iso=["HU"],
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        source_url="https://stipendiumhungaricum.hu/",
        currency="HUF",
        extras_insurance=True,
        extras_dormitory=True,
        description=(
            "Vengriya hukumati stipendiyasi. Kontrakt to'liq qoplanadi, oylik stipendiya, "
            "sog'liq sug'urtasi va yotoqxona (yoki turar joy nafaqasi) beriladi. Universitet "
            "va dastur cheklangan ro'yxatdan talabaning o'zi tomonidan tanlanadi.\n"
            f"{TODO_NOTE}"
        ),
    ),
    ScholarshipSeed(
        name="NAWA (Polsha davlat stipendiyasi)",
        country_iso=["PL"],
        coverage_type=CoverageType.PARTIAL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        source_url="https://nawa.gov.pl/en/students",
        currency="PLN",
        description=(
            "Polsha Milliy akademik almashinuv agentligi (NAWA) dasturlari. Qamrov dastur "
            "turiga qarab farq qiladi: ba'zi dasturlarda faqat oylik stipendiya beriladi "
            "(kontrakt alohida), ba'zilarida kontrakt ham qoplanadi — ariza berishdan oldin "
            "aniq dastur shartlarini tekshiring.\n"
            f"{TODO_NOTE}"
        ),
    ),
    ScholarshipSeed(
        name="Chevening (Buyuk Britaniya)",
        country_iso=["GB"],
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        source_url="https://www.chevening.org/",
        currency="GBP",
        extras_flight=True,
        description=(
            "Buyuk Britaniya hukumatining magistratura stipendiyasi (faqat 1 yillik master "
            "dasturlari). Kontrakt, yashash nafaqasi va aviachipta qoplanadi.\n"
            "Yosh chegarasi YO'Q — buning o'rniga kamida 2 yillik ish tajribasi va "
            "rahbarlik salohiyati talab qilinadi, shuning uchun 'yosh chegarasi' maydoni "
            "bo'sh qoldirilgan.\n"
            f"{TODO_NOTE}"
        ),
    ),
    ScholarshipSeed(
        name="Erasmus Mundus Joint Masters",
        country_iso=["DE", "HU", "PL"],
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        source_url="https://www.eacea.ec.europa.eu/scholarships/emjm-catalogue_en",
        currency="EUR",
        extras_insurance=True,
        extras_flight=True,
        description=(
            "Yevropa Ittifoqining qo'shma magistratura dasturi. Talaba kamida ikki xil "
            "davlatdagi universitetda o'qiydi, kontrakt, yashash nafaqasi, sug'urta va "
            "yo'l xarajatlari qoplanadi.\n"
            "Eslatma: dastur ko'plab EI davlatlarini qamrab oladi — bu yerda bazadagi "
            "mavjud davlatlar bilan bog'langan, to'liq ro'yxat rasmiy katalogda.\n"
            f"{TODO_NOTE}"
        ),
    ),
    ScholarshipSeed(
        name="Global Korea Scholarship (GKS)",
        country_iso=["KR"],
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        source_url="https://www.studyinkorea.go.kr/en/sub/gks/allnew_invite.do",
        currency="KRW",
        extras_flight=True,
        extras_insurance=True,
        extras_language_course=True,
        description=(
            "Janubiy Koreya hukumati stipendiyasi (ilgari KGSP). Kontrakt, oylik stipendiya, "
            "aviachipta, sug'urta va bir yillik koreys tili kursi qoplanadi. Ariza elchixona "
            "yoki universitet yo'nalishi orqali beriladi.\n"
            f"{TODO_NOTE}"
        ),
    ),
    ScholarshipSeed(
        name="Fulbright Foreign Student Program (AQSH)",
        country_iso=["US"],
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.ASSIGNED_BY_SCHOLARSHIP,
        source_url="https://foreign.fulbrightonline.org/",
        currency="USD",
        extras_flight=True,
        extras_insurance=True,
        description=(
            "AQSH Davlat departamentining magistratura/PhD stipendiyasi. Kontrakt, yashash "
            "nafaqasi, aviachipta va sug'urta qoplanadi. Universitet tanlovida komissiya "
            "ishtirok etadi, shuning uchun 'universitetni grant tayinlaydi' deb belgilangan.\n"
            f"{TODO_NOTE}"
        ),
    ),
    ScholarshipSeed(
        name="Türkiye Bursları",
        country_iso=["TR"],
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.ASSIGNED_BY_SCHOLARSHIP,
        source_url="https://turkiyeburslari.gov.tr/",
        currency="TRY",
        extras_flight=True,
        extras_insurance=True,
        extras_dormitory=True,
        extras_language_course=True,
        description=(
            "Turkiya hukumati stipendiyasi. Kontrakt, oylik stipendiya, yotoqxona, sug'urta, "
            "aviachipta va bir yillik turk tili kursi qoplanadi. Universitet va dasturni "
            "komissiya tayinlaydi (talaba tanlov ro'yxatini ko'rsatadi).\n"
            f"{TODO_NOTE}"
        ),
    ),
]


async def _upsert_countries(session: AsyncSession) -> dict[str, Country]:
    """ISO kod bo'yicha davlatni topadi yoki yaratadi."""
    existing = {
        c.iso_code: c
        for c in (await session.execute(select(Country))).scalars().all()
    }

    created = 0
    for seed in COUNTRIES:
        if seed.iso_code in existing:
            continue
        country = Country(
            name_uz=seed.name_uz,
            name_ru=seed.name_ru,
            name_en=seed.name_en,
            iso_code=seed.iso_code,
        )
        session.add(country)
        existing[seed.iso_code] = country
        created += 1

    await session.flush()
    if created:
        print(f"Davlatlar: {created} ta yangi qo'shildi")
    return existing


async def _upsert_scholarships(session: AsyncSession, countries: dict[str, Country]) -> None:
    existing = {
        s.name: s
        for s in (
            await session.execute(select(Scholarship).options(selectinload(Scholarship.countries)))
        )
        .scalars()
        .all()
    }

    now = datetime.now(UTC)
    created = updated = 0

    for seed in SCHOLARSHIPS:
        scholarship = existing.get(seed.name)
        if scholarship is None:
            scholarship = Scholarship(name=seed.name)
            session.add(scholarship)
            created += 1
        else:
            updated += 1

        scholarship.description = seed.description
        scholarship.coverage_type = seed.coverage_type
        scholarship.coverage_percent = seed.coverage_percent
        # stipend_amount ataylab tegilmaydi — admin panelda qo'lda to'ldiriladi.
        scholarship.currency = seed.currency
        scholarship.extras_flight = seed.extras_flight
        scholarship.extras_insurance = seed.extras_insurance
        scholarship.extras_dormitory = seed.extras_dormitory
        scholarship.extras_language_course = seed.extras_language_course
        scholarship.age_limit = seed.age_limit
        scholarship.citizenship_eligible = True
        scholarship.university_choice = seed.university_choice
        scholarship.application_linked_to_program = seed.application_linked_to_program
        scholarship.source_url = seed.source_url
        scholarship.verified_at = now
        scholarship.verified_by = VERIFIED_BY
        scholarship.countries = [countries[iso] for iso in seed.country_iso if iso in countries]

    print(f"Grantlar: {created} ta yangi, {updated} ta yangilandi")


async def main() -> None:
    async with async_session_factory() as session:
        try:
            countries = await _upsert_countries(session)
            await _upsert_scholarships(session, countries)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    print("Tayyor.")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
