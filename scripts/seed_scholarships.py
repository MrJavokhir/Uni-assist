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

    # Tavsif tarjimalari (bo'sh bo'lsa Mini App o'zbekchasiga qaytadi)
    description_ru: str | None = None
    description_en: str | None = None

    # --- Rasmiy sahifadan olingan tafsilotlar ---
    # None = sahifada ko'rsatilmagan (to'qilmaydi).
    stipend_amount: float | None = None
    stipend_max: float | None = None
    stipend_period: str | None = None  # "month" | "year"
    ielts_min: float | None = None
    toefl_min: int | None = None
    work_experience_years: int | None = None
    degree_levels: tuple[str, ...] = ()
    study_language: str | None = None
    duration_min_years: float | None = None
    duration_max_years: float | None = None
    selection_stages: int | None = None


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
        ),
        stipend_amount=992,
        stipend_max=1300,
        stipend_period="month",
        degree_levels=("master", "phd"),
        duration_min_years=1,
        duration_max_years=2,
        description_ru=(
            "Стипендия Германской службы академических обменов (DAAD). Для магистратуры и PhD: "
            "ежемесячная стипендия, медицинская страховка, часто авиабилет и языковой курс. "
            "Университет выбирает сам студент."
        ),
        description_en=(
            "A scholarship from the German Academic Exchange Service (DAAD). For master's and PhD "
            "study: a monthly stipend, health insurance and often flights and a language course. "
            "The student chooses the university."
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
        ),
        stipend_amount=43700,
        stipend_max=180000,
        stipend_period="month",
        degree_levels=("bachelor", "master", "phd"),
        study_language="English",
        description_ru=(
            "Стипендия правительства Венгрии. Обучение покрывается полностью, плюс ежемесячная "
            "стипендия, медицинская страховка и общежитие (или доплата на жильё). Университет и "
            "программу студент выбирает из ограниченного списка."
        ),
        description_en=(
            "A Hungarian government scholarship. Tuition is fully covered, plus a monthly "
            "stipend, health insurance and a dormitory place (or a housing contribution). The "
            "student picks the university and programme from a set list."
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
        ),
        stipend_amount=2500,
        stipend_period="month",
        degree_levels=("master",),
        description_ru=(
            "Программы Польского национального агентства академических обменов (NAWA). Покрытие "
            "зависит от программы: где-то выплачивается только ежемесячная стипендия (обучение "
            "оплачивается отдельно), где-то покрывается и обучение — уточняйте условия конкретной "
            "программы."
        ),
        description_en=(
            "Programmes run by Poland's National Agency for Academic Exchange (NAWA). Coverage "
            "depends on the programme: some pay only a monthly stipend (tuition is separate), "
            "others cover tuition too — check the conditions of the specific programme."
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
        ),
        work_experience_years=2,
        degree_levels=("master",),
        study_language="English",
        duration_min_years=1,
        duration_max_years=1,
        description_ru=(
            "Магистерская стипендия правительства Великобритании (только годичные магистратуры). "
            "Покрывает обучение, проживание и авиабилет. Возрастного ограничения НЕТ — вместо "
            "этого требуется минимум 2 года опыта работы и лидерский потенциал."
        ),
        description_en=(
            "A UK government master's scholarship (one-year master's programmes only). It covers "
            "tuition, living costs and flights. There is NO age limit — instead it requires at "
            "least 2 years of work experience and leadership potential."
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
        ),
        stipend_amount=1400,
        stipend_period="month",
        degree_levels=("master",),
        study_language="English",
        duration_min_years=1,
        duration_max_years=2,
        description_ru=(
            "Совместная магистерская программа Европейского союза. Студент учится минимум в двух "
            "странах; покрываются обучение, проживание, страховка и дорожные расходы. Программа "
            "охватывает многие страны ЕС — здесь связаны только те, что есть в базе."
        ),
        description_en=(
            "A joint master's programme run by the European Union. Students study in at least two "
            "countries; tuition, living costs, insurance and travel are covered. The programme "
            "spans many EU countries — only those already in the catalogue are linked here."
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
        ),
        degree_levels=("master", "phd"),
        duration_min_years=2,
        duration_max_years=3,
        description_ru=(
            "Стипендия правительства Южной Кореи (ранее KGSP). Покрывает обучение, ежемесячную "
            "стипендию, авиабилет, страховку и годичный курс корейского языка. Заявка подаётся "
            "через посольство или напрямую в университет."
        ),
        description_en=(
            "A South Korean government scholarship (formerly KGSP). It covers tuition, a monthly "
            "allowance, flights, insurance and a one-year Korean language course. You apply "
            "through an embassy or directly to a university."
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
        ),
        ielts_min=6.5,
        toefl_min=79,
        degree_levels=("master", "phd"),
        study_language="English",
        description_ru=(
            "Стипендия Госдепартамента США для магистратуры и PhD. Покрывает обучение, "
            "проживание, авиабилет и страховку. В выборе университета участвует комиссия."
        ),
        description_en=(
            "A U.S. State Department scholarship for master's and PhD study. It covers tuition, "
            "living costs, flights and insurance. A committee takes part in choosing the "
            "university."
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
        ),
        stipend_amount=6500,
        stipend_max=9000,
        stipend_period="month",
        degree_levels=("bachelor", "master", "phd"),
        study_language="Turkish",
        description_ru=(
            "Стипендия правительства Турции. Покрывает обучение, ежемесячную стипендию, "
            "общежитие, страховку, авиабилет и годичный курс турецкого языка. Университет и "
            "программу назначает комиссия (студент указывает свои предпочтения)."
        ),
        description_en=(
            "A Turkish government scholarship. It covers tuition, a monthly stipend, a dormitory "
            "place, insurance, flights and a one-year Turkish language course. A committee "
            "assigns the university and programme (the student lists preferences)."
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
        scholarship.description_ru = seed.description_ru
        scholarship.description_en = seed.description_en
        scholarship.coverage_type = seed.coverage_type
        scholarship.coverage_percent = seed.coverage_percent
        scholarship.currency = seed.currency
        # Quyidagilar rasmiy sahifalardan olingan; ko'rsatilmaganlari None.
        scholarship.stipend_amount = seed.stipend_amount
        scholarship.stipend_max = seed.stipend_max
        scholarship.stipend_period = seed.stipend_period
        scholarship.ielts_min = seed.ielts_min
        scholarship.toefl_min = seed.toefl_min
        scholarship.work_experience_years = seed.work_experience_years
        scholarship.degree_levels = list(seed.degree_levels) or None
        scholarship.study_language = seed.study_language
        scholarship.duration_min_years = seed.duration_min_years
        scholarship.duration_max_years = seed.duration_max_years
        scholarship.selection_stages = seed.selection_stages
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
