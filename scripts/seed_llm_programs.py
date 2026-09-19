"""LL.M. (Master of Laws) dasturlari — universitetlarning RASMIY sahifalaridan.

MANBA HAQIDA (muhim):
Bu ro'yxat llm-guide.com kabi vositachi kataloglardan KO'CHIRILMAGAN. Har bir
yozuvning `source_url`i universitetning o'z sahifasi va har bir raqam (kontrakt,
IELTS/TOEFL, muddat) o'sha sahifada aynan shunday yozilgan.

TO'QILMAGAN MA'LUMOT:
Rasmiy sahifada ko'rsatilmagan maydon BO'SH qoldiriladi — taxmin qilinmaydi.
Masalan NYU faqat kredit narxini e'lon qiladi (yillik summa emas), shuning
uchun uning ProgramCost yozuvi yaratilmaydi. Bo'sh maydonlarni admin panelda
"Universitet qo'shish" sehrgari orqali to'ldirish mumkin.

Idempotent: universitet (nomi) va dastur (universitet + nomi + daraja) bo'yicha
upsert qilinadi — ikki marta ishga tushirilsa ham dublikat yaratmaydi.

Ishlatish:
    uv run python scripts/seed_llm_programs.py
"""

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Country,
    Deadline,
    DeadlineType,
    DegreeLevel,
    Program,
    ProgramCost,
    ProgramRequirement,
    University,
)
from app.db.session import async_session_factory

VERIFIED_BY = "seed-llm-official"
FIELD_OF_STUDY = "Law"


@dataclass(frozen=True)
class LlmSeed:
    """Bitta LL.M. dasturi va uning universiteti.

    `None` qiymat = rasmiy sahifada ko'rsatilmagan (to'qilmaydi).
    """

    country_iso: str
    university: str
    city: str
    website: str
    timezone: str

    program: str
    source_url: str
    intake_term: str
    duration_years: float = 1.0
    language: str = "Ingliz tili"
    abbreviation: str = "LLM"

    tuition_amount: float | None = None
    tuition_currency: str = "USD"
    ielts_min: float | None = None
    toefl_min: int | None = None
    deadline_close: date | None = None
    notes: str | None = None
    # Universitet logotipi saytdan avtomatik olinadi, shuning uchun bu yerda
    # ataylab yo'q (app/webapp/api.py `_logo_url`).
    missing: tuple[str, ...] = field(default_factory=tuple)


# Har bir qiymat 2026-yil sentyabr holatiga ko'ra rasmiy sahifadan olingan.
SEEDS: list[LlmSeed] = [
    # ------------------------------- AQSH -------------------------------
    LlmSeed(
        country_iso="US",
        university="Harvard Law School",
        city="Cambridge, MA",
        website="https://hls.harvard.edu",
        timezone="America/New_York",
        program="Master of Laws (LL.M.)",
        source_url="https://hls.harvard.edu/graduate-program/graduate-program-admissions-and-financial-aid/apply-to-the-graduate-program/",
        intake_term="2027 Fall",
        deadline_close=date(2026, 12, 1),
        missing=("kontrakt", "IELTS/TOEFL"),
    ),
    LlmSeed(
        country_iso="US",
        university="Columbia Law School",
        city="Nyu-York, NY",
        website="https://www.law.columbia.edu",
        timezone="America/New_York",
        program="Master of Laws (LL.M.)",
        source_url="https://www.law.columbia.edu/admissions/graduate-admissions/llm/llm-tuition-and-fees",
        intake_term="2027 Fall",
        tuition_amount=93757,
        tuition_currency="USD",
        # 2026-yil 21-yanvargacha bo'lgan TOEFL iBT shkalasi bo'yicha.
        # Yangi shkalada talab: umumiy 5.5, har bo'limda kamida 5.0.
        toefl_min=105,
        missing=("IELTS", "ariza yopilish sanasi"),
    ),
    LlmSeed(
        country_iso="US",
        university="Georgetown University Law Center",
        city="Vashington, DC",
        website="https://www.law.georgetown.edu",
        timezone="America/New_York",
        program="International Legal Studies LL.M.",
        source_url="https://www.law.georgetown.edu/academics/llm-degree-programs/international-legal-studies/",
        intake_term="2027 Fall",
        toefl_min=100,
        missing=("kontrakt", "IELTS", "ariza yopilish sanasi"),
    ),
    LlmSeed(
        country_iso="US",
        university="New York University School of Law",
        city="Nyu-York, NY",
        website="https://www.law.nyu.edu",
        timezone="America/New_York",
        program="Master of Laws (LL.M.)",
        source_url="https://www.law.nyu.edu/graduateadmissions/whentoapply",
        intake_term="2027 Fall",
        # NYU yillik summani e'lon qilmaydi — faqat kredit narxi. Kreditni
        # ko'paytirib "yillik" raqam chiqarish noto'g'ri bo'lardi.
        missing=("kontrakt", "IELTS/TOEFL", "ariza yopilish sanasi"),
    ),
    # --------------------------- Buyuk Britaniya ---------------------------
    LlmSeed(
        country_iso="GB",
        university="London School of Economics and Political Science",
        city="London",
        website="https://www.lse.ac.uk",
        timezone="Europe/London",
        program="LLM, Master of Laws",
        source_url="https://www.lse.ac.uk/study-at-lse/graduate/llm",
        intake_term="2026 Fall",
        tuition_amount=39900,
        tuition_currency="GBP",
        notes="Ariza qabul qilish uzluksiz (rolling admissions) — qat'iy yopilish sanasi yo'q.",
        missing=("IELTS/TOEFL",),
    ),
    LlmSeed(
        country_iso="GB",
        university="Queen Mary University of London",
        city="London",
        website="https://www.qmul.ac.uk",
        timezone="Europe/London",
        program="Laws LLM",
        source_url="https://www.qmul.ac.uk/postgraduate/taught/coursefinder/courses/laws-llm/",
        intake_term="2026 Fall",
        # IELTS (Academic): umumiy 7.0, Writing 6.5, qolganlari 6.0.
        ielts_min=7.0,
        missing=("kontrakt", "ariza yopilish sanasi"),
    ),
    # ------------------------------ Germaniya ------------------------------
    LlmSeed(
        country_iso="DE",
        university="Bucerius Law School",
        city="Gamburg",
        website="https://www.law-school.de",
        timezone="Europe/Berlin",
        program="Master of Law and Business (LL.M.)",
        source_url="https://www.law-school.de/international/education/master-of-law-and-business",
        intake_term="2027 Fall",
        tuition_amount=25000,
        tuition_currency="EUR",
        deadline_close=date(2027, 1, 15),
        notes=(
            "LL.M. darajasi faqat birinchi diplomi huquq bo'yicha bo'lganlarga beriladi; "
            "boshqalar MLB oladi. Dasturga 8 haftalik amaliyot kiradi. 15-yanvargacha "
            "ariza bergan va 1-aprelgacha to'lovni tasdiqlaganlarga 2 000 EUR chegirma."
        ),
        missing=("IELTS/TOEFL",),
    ),
    # ------------------------------- Italiya -------------------------------
    LlmSeed(
        country_iso="IT",
        university="Bocconi University",
        city="Milan",
        website="https://www.unibocconi.it",
        timezone="Europe/Rome",
        program="LLM in Law of Technology and Automated Systems",
        source_url="https://www.unibocconi.it/en/programs/specialized-masters-programs/llm-law-technology-and-automated-systems/fee-and-financial-aid",
        intake_term="2026 Fall",
        tuition_amount=16000,
        tuition_currency="EUR",
        notes="Narx 2026/27 nashri uchun; o'quv materiallari va kampus xizmatlari kiradi.",
        missing=("IELTS/TOEFL", "ariza yopilish sanasi"),
    ),
    # ------------------------------- Chexiya -------------------------------
    LlmSeed(
        country_iso="CZ",
        university="Charles University, Faculty of Law",
        city="Praga",
        website="https://www.prf.cuni.cz",
        timezone="Europe/Prague",
        program="LL.M. Programme",
        source_url="https://www.prf.cuni.cz/en/llm/apply-now",
        intake_term="2027 Fall",
        tuition_amount=6950,
        tuition_currency="USD",
        deadline_close=date(2027, 4, 30),
        notes=(
            "Muddat viza talab qilinadigan arizachilar uchun (O'zbekiston fuqarolari shunga "
            "kiradi); vizasizlar uchun 1-iyul. Ariza yig'imi 200 USD, qaytarilmaydi. "
            "Erta ariza bergan va 14 kun ichida to'laganlarga narx 6 200 USD."
        ),
        missing=("IELTS/TOEFL",),
    ),
]

NOTE_PREFIX = "Rasmiy sahifadan tekshirilgan."
MISSING_HINT = (
    "Rasmiy sahifada ko'rsatilmagan va shuning uchun bo'sh qoldirilgan: {fields}. "
    "Admin panelda 'Universitet qo'shish' sehrgari orqali to'ldiring."
)


def _build_notes(seed: LlmSeed) -> str:
    parts = [NOTE_PREFIX]
    if seed.notes:
        parts.append(seed.notes)
    if seed.missing:
        parts.append(MISSING_HINT.format(fields=", ".join(seed.missing)))
    return " ".join(parts)


async def _countries_by_iso(session: AsyncSession) -> dict[str, Country]:
    rows = (await session.execute(select(Country))).scalars().all()
    return {c.iso_code: c for c in rows}


async def _upsert_universities(
    session: AsyncSession, countries: dict[str, Country]
) -> tuple[dict[str, University], int, int]:
    existing = {u.name: u for u in (await session.execute(select(University))).scalars().all()}

    created = updated = 0
    for seed in SEEDS:
        country = countries.get(seed.country_iso)
        if country is None:
            raise RuntimeError(
                f"'{seed.country_iso}' davlati bazada yo'q. Avval "
                "scripts/seed_top_destinations.py ni ishga tushiring."
            )

        university = existing.get(seed.university)
        if university is None:
            university = University(name=seed.university)
            session.add(university)
            existing[seed.university] = university
            created += 1
        else:
            updated += 1

        university.country_id = country.id
        university.city = seed.city
        university.website = seed.website
        university.timezone = seed.timezone

    await session.flush()
    return existing, created, updated


async def _upsert_programs(
    session: AsyncSession, universities: dict[str, University]
) -> tuple[int, int]:
    rows = (await session.execute(select(Program))).scalars().all()
    existing = {(p.university_id, p.name, p.degree_level): p for p in rows}

    now = datetime.now(UTC)
    created = updated = 0

    for seed in SEEDS:
        university = universities[seed.university]
        key = (university.id, seed.program, DegreeLevel.MASTER)

        program = existing.get(key)
        if program is None:
            program = Program(
                university_id=university.id,
                name=seed.program,
                degree_level=DegreeLevel.MASTER,
            )
            session.add(program)
            existing[key] = program
            created += 1
        else:
            updated += 1

        program.abbreviation = seed.abbreviation
        program.field_of_study = FIELD_OF_STUDY
        program.language_of_instruction = seed.language
        program.duration_years = seed.duration_years
        program.intake_term = seed.intake_term
        program.notes = _build_notes(seed)
        program.source_url = seed.source_url
        program.verified_at = now
        program.verified_by = VERIFIED_BY
        await session.flush()

        await _replace_details(session, program, seed, now)

    return created, updated


async def _replace_details(
    session: AsyncSession, program: Program, seed: LlmSeed, now: datetime
) -> None:
    """Talab/xarajat/muddat yozuvlarini qayta yozadi.

    Skript ikkinchi marta ishga tushirilganda eskilari o'chirilib, seed'dagi
    qiymatlar bilan almashtiriladi — shunda dublikat ham, eskirgan raqam ham
    qolmaydi.
    """
    for model in (ProgramRequirement, ProgramCost, Deadline):
        for row in (
            (await session.execute(select(model).where(model.program_id == program.id)))
            .scalars()
            .all()
        ):
            await session.delete(row)
    await session.flush()

    if seed.ielts_min is not None or seed.toefl_min is not None:
        session.add(
            ProgramRequirement(
                program_id=program.id,
                ielts_min=seed.ielts_min,
                toefl_min=seed.toefl_min,
            )
        )

    if seed.tuition_amount is not None:
        session.add(
            ProgramCost(
                program_id=program.id,
                tuition_amount=seed.tuition_amount,
                currency=seed.tuition_currency,
                last_checked=now.date(),
            )
        )

    if seed.deadline_close is not None:
        session.add(
            Deadline(
                program_id=program.id,
                type=DeadlineType.APPLICATION_CLOSE,
                date_utc=datetime(
                    seed.deadline_close.year,
                    seed.deadline_close.month,
                    seed.deadline_close.day,
                    tzinfo=UTC,
                ),
                intake_term=seed.intake_term,
            )
        )


async def main() -> None:
    async with async_session_factory() as session:
        try:
            countries = await _countries_by_iso(session)
            universities, uni_created, uni_updated = await _upsert_universities(session, countries)
            prog_created, prog_updated = await _upsert_programs(session, universities)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    with_tuition = sum(1 for s in SEEDS if s.tuition_amount is not None)
    with_scores = sum(1 for s in SEEDS if s.ielts_min or s.toefl_min)
    with_deadline = sum(1 for s in SEEDS if s.deadline_close is not None)

    print(f"Universitetlar: {uni_created} ta yangi, {uni_updated} ta yangilandi")
    print(f"LL.M. dasturlari: {prog_created} ta yangi, {prog_updated} ta yangilandi")
    print(
        f"Tasdiqlangan qiymatlar: {with_tuition}/{len(SEEDS)} kontrakt, "
        f"{with_scores}/{len(SEEDS)} til bali, {with_deadline}/{len(SEEDS)} muddat"
    )


if __name__ == "__main__":
    asyncio.run(main())
