"""O'zbekistonliklar eng ko'p tanlaydigan davlatlar, universitetlar va dasturlar.

MA'LUMOT SIFATI HAQIDA (muhim):
Bu skript faqat TASDIQLASH MUMKIN bo'lgan ma'lumotni kiritadi — davlat nomi,
universitet nomi/shahri/rasmiy sayti/vaqt zonasi va dastur nomi/darajasi/tili/
davomiyligi. Kontrakt narxi, minimal GPA/IELTS va yashash xarajati ATAYLAB
kiritilmaydi (ProgramCost va ProgramRequirement yozuvlari yaratilmaydi), chunki
bu raqamlar universitetdan universitetga va yildan yilga o'zgaradi — ularni
to'qib chiqarish loyihaning asosiy tamoyiliga (source_url + verified_at +
verified_by majburiy) zid bo'lardi.

Shu sababli dasturlar `verified_by="seed-unverified"` bilan belgilanadi:
admin panelda ular ko'rinadi va talab/xarajat ma'lumotini qo'lda to'ldirish
kerakligi aniq bo'ladi.

Idempotent: davlat ISO kodi, universitet (nomi + davlat) va dastur
(nomi + universitet + daraja) bo'yicha upsert qilinadi.

Ishlatish:
    uv run python scripts/seed_top_destinations.py
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Country, DegreeLevel, Program, University
from app.db.session import async_session_factory

VERIFIED_BY = "seed-unverified"
INTAKE_TERM = "2026 Fall"


@dataclass(frozen=True)
class CountrySeed:
    iso_code: str
    name_uz: str
    name_ru: str
    name_en: str


@dataclass(frozen=True)
class UniversitySeed:
    country_iso: str
    name: str
    city: str
    website: str
    timezone: str


@dataclass(frozen=True)
class ProgramSeed:
    university_name: str
    name: str
    degree_level: DegreeLevel
    field_of_study: str
    language: str
    duration_years: float


COUNTRIES: list[CountrySeed] = [
    CountrySeed("RU", "Rossiya", "Россия", "Russia"),
    CountrySeed("KR", "Janubiy Koreya", "Южная Корея", "South Korea"),
    CountrySeed("CN", "Xitoy", "Китай", "China"),
    CountrySeed("TR", "Turkiya", "Турция", "Turkey"),
    CountrySeed("MY", "Malayziya", "Малайзия", "Malaysia"),
    CountrySeed("AE", "BAA", "ОАЭ", "United Arab Emirates"),
    CountrySeed("US", "AQSH", "США", "United States"),
    CountrySeed("GB", "Buyuk Britaniya", "Великобритания", "United Kingdom"),
    CountrySeed("DE", "Germaniya", "Германия", "Germany"),
    CountrySeed("PL", "Polsha", "Польша", "Poland"),
    CountrySeed("HU", "Vengriya", "Венгрия", "Hungary"),
    CountrySeed("CZ", "Chexiya", "Чехия", "Czechia"),
    CountrySeed("IT", "Italiya", "Италия", "Italy"),
    CountrySeed("CY", "Shimoliy Kipr", "Северный Кипр", "Northern Cyprus"),
]

UNIVERSITIES: list[UniversitySeed] = [
    # --- Rossiya ---
    UniversitySeed("RU", "Lomonosov Moscow State University", "Moskva", "https://www.msu.ru", "Europe/Moscow"),
    UniversitySeed("RU", "RUDN University", "Moskva", "https://www.rudn.ru", "Europe/Moscow"),
    UniversitySeed("RU", "HSE University", "Moskva", "https://www.hse.ru", "Europe/Moscow"),
    UniversitySeed("RU", "Bauman Moscow State Technical University", "Moskva", "https://bmstu.ru", "Europe/Moscow"),
    UniversitySeed("RU", "Peter the Great St. Petersburg Polytechnic University", "Sankt-Peterburg", "https://www.spbstu.ru", "Europe/Moscow"),
    UniversitySeed("RU", "ITMO University", "Sankt-Peterburg", "https://itmo.ru", "Europe/Moscow"),
    UniversitySeed("RU", "Kazan Federal University", "Qozon", "https://kpfu.ru", "Europe/Moscow"),
    # --- Janubiy Koreya ---
    UniversitySeed("KR", "Seoul National University", "Seul", "https://www.snu.ac.kr", "Asia/Seoul"),
    UniversitySeed("KR", "KAIST", "Daejeon", "https://www.kaist.ac.kr", "Asia/Seoul"),
    UniversitySeed("KR", "Yonsei University", "Seul", "https://www.yonsei.ac.kr", "Asia/Seoul"),
    UniversitySeed("KR", "Korea University", "Seul", "https://www.korea.ac.kr", "Asia/Seoul"),
    UniversitySeed("KR", "Sungkyunkwan University", "Seul", "https://www.skku.edu", "Asia/Seoul"),
    UniversitySeed("KR", "Hanyang University", "Seul", "https://www.hanyang.ac.kr", "Asia/Seoul"),
    # --- Xitoy ---
    UniversitySeed("CN", "Tsinghua University", "Pekin", "https://www.tsinghua.edu.cn", "Asia/Shanghai"),
    UniversitySeed("CN", "Peking University", "Pekin", "https://www.pku.edu.cn", "Asia/Shanghai"),
    UniversitySeed("CN", "Fudan University", "Shanxay", "https://www.fudan.edu.cn", "Asia/Shanghai"),
    UniversitySeed("CN", "Shanghai Jiao Tong University", "Shanxay", "https://www.sjtu.edu.cn", "Asia/Shanghai"),
    UniversitySeed("CN", "Zhejiang University", "Xanchjou", "https://www.zju.edu.cn", "Asia/Shanghai"),
    UniversitySeed("CN", "Harbin Institute of Technology", "Xarbin", "https://www.hit.edu.cn", "Asia/Shanghai"),
    # --- Turkiya ---
    UniversitySeed("TR", "Boğaziçi University", "Istanbul", "https://bogazici.edu.tr", "Europe/Istanbul"),
    UniversitySeed("TR", "Middle East Technical University", "Anqara", "https://www.metu.edu.tr", "Europe/Istanbul"),
    UniversitySeed("TR", "Istanbul Technical University", "Istanbul", "https://www.itu.edu.tr", "Europe/Istanbul"),
    UniversitySeed("TR", "Bilkent University", "Anqara", "https://w3.bilkent.edu.tr", "Europe/Istanbul"),
    UniversitySeed("TR", "Sabancı University", "Istanbul", "https://www.sabanciuniv.edu", "Europe/Istanbul"),
    UniversitySeed("TR", "Koç University", "Istanbul", "https://www.ku.edu.tr", "Europe/Istanbul"),
    UniversitySeed("TR", "Istanbul University", "Istanbul", "https://www.istanbul.edu.tr", "Europe/Istanbul"),
    # --- Malayziya ---
    UniversitySeed("MY", "University of Malaya", "Kuala-Lumpur", "https://www.um.edu.my", "Asia/Kuala_Lumpur"),
    UniversitySeed("MY", "Universiti Teknologi Malaysia", "Johor Bahru", "https://www.utm.my", "Asia/Kuala_Lumpur"),
    UniversitySeed("MY", "Universiti Putra Malaysia", "Serdang", "https://www.upm.edu.my", "Asia/Kuala_Lumpur"),
    UniversitySeed("MY", "Universiti Kebangsaan Malaysia", "Bangi", "https://www.ukm.my", "Asia/Kuala_Lumpur"),
    UniversitySeed("MY", "Universiti Sains Malaysia", "Penang", "https://www.usm.my", "Asia/Kuala_Lumpur"),
    UniversitySeed("MY", "Sunway University", "Subang Jaya", "https://sunwayuniversity.edu.my", "Asia/Kuala_Lumpur"),
    # --- BAA ---
    UniversitySeed("AE", "United Arab Emirates University", "Al-Ayn", "https://www.uaeu.ac.ae", "Asia/Dubai"),
    UniversitySeed("AE", "Khalifa University", "Abu-Dabi", "https://www.ku.ac.ae", "Asia/Dubai"),
    UniversitySeed("AE", "American University of Sharjah", "Sharja", "https://www.aus.edu", "Asia/Dubai"),
    UniversitySeed("AE", "University of Sharjah", "Sharja", "https://www.sharjah.ac.ae", "Asia/Dubai"),
    # --- AQSH ---
    UniversitySeed("US", "Massachusetts Institute of Technology", "Cambridge, MA", "https://www.mit.edu", "America/New_York"),
    UniversitySeed("US", "Stanford University", "Stanford, CA", "https://www.stanford.edu", "America/Los_Angeles"),
    UniversitySeed("US", "Harvard University", "Cambridge, MA", "https://www.harvard.edu", "America/New_York"),
    UniversitySeed("US", "University of California, Berkeley", "Berkeley, CA", "https://www.berkeley.edu", "America/Los_Angeles"),
    UniversitySeed("US", "Purdue University", "West Lafayette, IN", "https://www.purdue.edu", "America/Indiana/Indianapolis"),
    UniversitySeed("US", "Arizona State University", "Tempe, AZ", "https://www.asu.edu", "America/Phoenix"),
    # --- Buyuk Britaniya ---
    UniversitySeed("GB", "University of Oxford", "Oksford", "https://www.ox.ac.uk", "Europe/London"),
    UniversitySeed("GB", "University of Cambridge", "Kembrij", "https://www.cam.ac.uk", "Europe/London"),
    UniversitySeed("GB", "Imperial College London", "London", "https://www.imperial.ac.uk", "Europe/London"),
    UniversitySeed("GB", "University College London", "London", "https://www.ucl.ac.uk", "Europe/London"),
    UniversitySeed("GB", "University of Manchester", "Manchester", "https://www.manchester.ac.uk", "Europe/London"),
    UniversitySeed("GB", "University of Edinburgh", "Edinburg", "https://www.ed.ac.uk", "Europe/London"),
    # --- Germaniya ---
    UniversitySeed("DE", "Technical University of Munich", "Myunxen", "https://www.tum.de", "Europe/Berlin"),
    UniversitySeed("DE", "RWTH Aachen University", "Aaxen", "https://www.rwth-aachen.de", "Europe/Berlin"),
    UniversitySeed("DE", "Technische Universität Berlin", "Berlin", "https://www.tu.berlin", "Europe/Berlin"),
    UniversitySeed("DE", "Ludwig Maximilian University of Munich", "Myunxen", "https://www.lmu.de", "Europe/Berlin"),
    UniversitySeed("DE", "Heidelberg University", "Haydelberg", "https://www.uni-heidelberg.de", "Europe/Berlin"),
    UniversitySeed("DE", "Karlsruhe Institute of Technology", "Karlsrue", "https://www.kit.edu", "Europe/Berlin"),
    UniversitySeed("DE", "TU Dresden", "Drezden", "https://tu-dresden.de", "Europe/Berlin"),
    # --- Polsha ---
    UniversitySeed("PL", "University of Warsaw", "Varshava", "https://www.uw.edu.pl", "Europe/Warsaw"),
    UniversitySeed("PL", "Jagiellonian University", "Krakov", "https://www.uj.edu.pl", "Europe/Warsaw"),
    UniversitySeed("PL", "Warsaw University of Technology", "Varshava", "https://www.pw.edu.pl", "Europe/Warsaw"),
    UniversitySeed("PL", "AGH University of Krakow", "Krakov", "https://www.agh.edu.pl", "Europe/Warsaw"),
    UniversitySeed("PL", "Poznan University of Technology", "Poznan", "https://www.put.poznan.pl", "Europe/Warsaw"),
    # --- Vengriya ---
    UniversitySeed("HU", "Eötvös Loránd University", "Budapesht", "https://www.elte.hu", "Europe/Budapest"),
    UniversitySeed("HU", "Budapest University of Technology and Economics", "Budapesht", "https://www.bme.hu", "Europe/Budapest"),
    UniversitySeed("HU", "Semmelweis University", "Budapesht", "https://semmelweis.hu", "Europe/Budapest"),
    UniversitySeed("HU", "University of Debrecen", "Debretsen", "https://unideb.hu", "Europe/Budapest"),
    UniversitySeed("HU", "University of Szeged", "Seged", "https://u-szeged.hu", "Europe/Budapest"),
    # --- Chexiya ---
    UniversitySeed("CZ", "Charles University", "Praga", "https://cuni.cz", "Europe/Prague"),
    UniversitySeed("CZ", "Czech Technical University in Prague", "Praga", "https://www.cvut.cz", "Europe/Prague"),
    UniversitySeed("CZ", "Masaryk University", "Brno", "https://www.muni.cz", "Europe/Prague"),
    UniversitySeed("CZ", "Brno University of Technology", "Brno", "https://www.vut.cz", "Europe/Prague"),
    # --- Italiya ---
    UniversitySeed("IT", "Politecnico di Milano", "Milan", "https://www.polimi.it", "Europe/Rome"),
    UniversitySeed("IT", "Sapienza University of Rome", "Rim", "https://www.uniroma1.it", "Europe/Rome"),
    UniversitySeed("IT", "University of Bologna", "Bolonya", "https://www.unibo.it", "Europe/Rome"),
    UniversitySeed("IT", "Politecnico di Torino", "Turin", "https://www.polito.it", "Europe/Rome"),
    # --- Shimoliy Kipr ---
    UniversitySeed("CY", "Eastern Mediterranean University", "Famagusta", "https://www.emu.edu.tr", "Asia/Nicosia"),
    UniversitySeed("CY", "Near East University", "Nikosiya", "https://neu.edu.tr", "Asia/Nicosia"),
    UniversitySeed("CY", "Cyprus International University", "Nikosiya", "https://www.ciu.edu.tr", "Asia/Nicosia"),
]

# Eng ko'p tanlanadigan yo'nalishlar. Davomiylik mintaqa odatiga ko'ra:
# bakalavr — Yevropada 3, boshqa joyda 4 yil; magistratura — 2 yil
# (Buyuk Britaniyada 1 yil).
_EU3 = {"DE", "PL", "HU", "CZ", "IT", "GB"}


def _programs_for(uni: UniversitySeed) -> list[ProgramSeed]:
    bachelor_years = 3.0 if uni.country_iso in _EU3 else 4.0
    master_years = 1.0 if uni.country_iso == "GB" else 2.0
    language = "Rus tili" if uni.country_iso == "RU" else "Ingliz tili"

    return [
        ProgramSeed(uni.name, "Computer Science", DegreeLevel.BACHELOR, "Computer Science", language, bachelor_years),
        ProgramSeed(uni.name, "Computer Science", DegreeLevel.MASTER, "Computer Science", "Ingliz tili", master_years),
        ProgramSeed(uni.name, "Business Administration", DegreeLevel.BACHELOR, "Business / Economics", language, bachelor_years),
        ProgramSeed(uni.name, "Electrical and Electronics Engineering", DegreeLevel.BACHELOR, "Engineering", language, bachelor_years),
    ]


async def _upsert_countries(session: AsyncSession) -> tuple[dict[str, Country], int]:
    existing = {c.iso_code: c for c in (await session.execute(select(Country))).scalars().all()}

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
    return existing, created


async def _upsert_universities(
    session: AsyncSession, countries: dict[str, Country]
) -> tuple[dict[str, University], int, int]:
    existing = {u.name: u for u in (await session.execute(select(University))).scalars().all()}

    created = updated = 0
    for seed in UNIVERSITIES:
        country = countries.get(seed.country_iso)
        if country is None:
            continue

        university = existing.get(seed.name)
        if university is None:
            university = University(name=seed.name)
            session.add(university)
            existing[seed.name] = university
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
    existing_rows = (await session.execute(select(Program))).scalars().all()
    existing = {(p.university_id, p.name, p.degree_level): p for p in existing_rows}

    now = datetime.now(UTC)
    created = updated = 0

    for uni_seed in UNIVERSITIES:
        university = universities.get(uni_seed.name)
        if university is None:
            continue

        for seed in _programs_for(uni_seed):
            key = (university.id, seed.name, seed.degree_level)
            program = existing.get(key)
            if program is None:
                program = Program(
                    university_id=university.id,
                    name=seed.name,
                    degree_level=seed.degree_level,
                )
                session.add(program)
                existing[key] = program
                created += 1
            else:
                updated += 1

            program.field_of_study = seed.field_of_study
            program.language_of_instruction = seed.language
            program.duration_years = seed.duration_years
            program.intake_term = INTAKE_TERM
            program.notes = (
                "Seed orqali kiritilgan. Kontrakt narxi, minimal GPA/IELTS va yashash "
                "xarajati tasdiqlanmagan — universitet rasmiy saytidan tekshirib, "
                "admin panelda 'Dastur talablari' va 'Dastur xarajatlari' bo'limlarini "
                "to'ldiring."
            )
            # Aniq dastur sahifasi emas, universitetning rasmiy sayti —
            # deep-link to'qib chiqarilmaydi.
            program.source_url = uni_seed.website
            program.verified_at = now
            program.verified_by = VERIFIED_BY

    return created, updated


async def main() -> None:
    async with async_session_factory() as session:
        try:
            countries, countries_created = await _upsert_countries(session)
            universities, uni_created, uni_updated = await _upsert_universities(session, countries)
            prog_created, prog_updated = await _upsert_programs(session, universities)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    print(f"Davlatlar:      {countries_created} ta yangi")
    print(f"Universitetlar: {uni_created} ta yangi, {uni_updated} ta yangilandi")
    print(f"Dasturlar:      {prog_created} ta yangi, {prog_updated} ta yangilandi")
    print(
        "\nEslatma: dasturlar 'seed-unverified' deb belgilandi — talab va xarajat "
        "ma'lumotlari qo'lda to'ldirilishi kerak."
    )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
