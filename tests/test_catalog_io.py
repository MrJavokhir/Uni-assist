"""CSV import/eksport: o'qish, tekshirish (oldindan ko'rish) va saqlash."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.catalog_io import (
    MAX_ROWS,
    STATUS_ERROR,
    STATUS_NEW,
    STATUS_UNCHANGED,
    STATUS_UPDATE,
    CsvFileError,
    apply_plan,
    build_plan,
    export_csv,
    parse_csv,
    template_csv,
)
from app.db.models import (
    Country,
    CoverageType,
    DegreeLevel,
    Field,
    Program,
    Scholarship,
    University,
    UniversityChoiceType,
)

PROGRAMS_HEADER = (
    "country_iso,university_name,name,abbreviation,degree_level,field_code,"
    "language_of_instruction,duration_years,intake_term,source_url,notes,notes_ru,notes_en"
)


def _csv(*lines: str) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


async def _seed(session: AsyncSession) -> University:
    session.add_all([
        Field(code="cs_it", name_uz="IT", name_ru="ИТ", name_en="IT", sort_order=1),
        Field(code="law", name_uz="Huquq", name_ru="Право", name_en="Law", sort_order=2),
    ])
    country = Country(name_uz="Germaniya", name_ru="Германия", name_en="Germany", iso_code="DE")
    session.add(country)
    await session.flush()
    university = University(
        country_id=country.id, name="TU Munich", city="Munich", timezone="Europe/Berlin"
    )
    session.add(university)
    await session.commit()
    return university


async def _plan(session, **files: bytes):
    parsed = {kind: parse_csv(data, kind) for kind, data in files.items()}
    return await build_plan(session, parsed)


async def _import(session, **files: bytes):
    plan = await _plan(session, **files)
    assert not plan.has_errors, [(r.line, r.errors) for r in plan.rows if r.errors]
    await apply_plan(session, plan, admin="tester")
    await session.commit()
    return plan


async def _count(session, model) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


# ------------------------------ to'g'ri fayl ------------------------------


async def test_valid_file_creates_program(session: AsyncSession):
    await _seed(session)
    data = _csv(
        PROGRAMS_HEADER,
        "DE,TU Munich,Informatics,M.Sc.,master,cs_it,English,2,2027 Winter,https://tum.de/i,,,",
    )

    plan = await _plan(session, programs=data)
    assert [r.status for r in plan.rows] == [STATUS_NEW]

    # Oldindan ko'rish bazaga hech narsa yozmaydi.
    assert await _count(session, Program) == 0

    await apply_plan(session, plan, admin="tester")
    await session.commit()
    program = (await session.execute(select(Program))).scalar_one()
    assert program.name == "Informatics"
    assert program.degree_level == DegreeLevel.MASTER
    assert program.language_of_instruction == "English"
    assert program.verified_by == "tester"
    assert (datetime.now(UTC) - program.verified_at).total_seconds() < 60


async def test_countries_universities_programs_in_one_import(session: AsyncSession):
    """Bitta importda yangi davlat -> yangi universitet -> yangi dastur."""
    await _seed(session)
    countries = _csv("iso_code,name_uz,name_ru,name_en", "KR,Koreya,Корея,Korea")
    universities = _csv(
        "country_iso,name,city,website,timezone,logo_url,ranking",
        "KR,KAIST,Daejeon,https://kaist.ac.kr,Asia/Seoul,,53",
    )
    programs = _csv(
        PROGRAMS_HEADER,
        "KR,KAIST,Computer Science,,bachelor,cs_it,Korean,4,Fall,https://kaist.ac.kr/cs,,,",
    )

    plan = await _import(
        session, countries=countries, universities=universities, programs=programs
    )

    assert [r.status for r in plan.rows] == [STATUS_NEW] * 3
    kaist = (await session.execute(select(University).where(University.name == "KAIST"))).scalar_one()
    assert kaist.ranking == 53
    assert await _count(session, Program) == 1


# ------------------------------ tekshiruvlar ------------------------------


async def test_unknown_field_code_is_an_error(session: AsyncSession):
    await _seed(session)
    data = _csv(
        PROGRAMS_HEADER,
        "DE,TU Munich,Informatics,,master,computer_science,English,2,Fall,https://x.de,,,",
    )

    plan = await _plan(session, programs=data)

    assert plan.has_errors
    assert plan.rows[0].status == STATUS_ERROR
    assert any("field_code" in e for e in plan.rows[0].errors)
    with pytest.raises(ValueError):
        await apply_plan(session, plan, admin="tester")


async def test_bad_degree_level_is_an_error(session: AsyncSession):
    await _seed(session)
    data = _csv(
        PROGRAMS_HEADER,
        "DE,TU Munich,Informatics,,masters,cs_it,English,2,Fall,https://x.de,,,",
    )

    plan = await _plan(session, programs=data)

    assert plan.rows[0].status == STATUS_ERROR
    assert any("degree_level" in e for e in plan.rows[0].errors)


async def test_unknown_language_and_timezone_are_errors(session: AsyncSession):
    await _seed(session)
    universities = _csv(
        "country_iso,name,city,website,timezone,logo_url,ranking",
        "DE,LMU,Munich,,Europe/Munchen,,",
    )
    programs = _csv(
        PROGRAMS_HEADER,
        "DE,TU Munich,Informatics,,master,cs_it,Ingliz tili,2,Fall,https://x.de,,,",
    )

    plan = await _plan(session, universities=universities, programs=programs)

    assert any("timezone" in e for e in plan.rows[0].errors)
    assert any("language_of_instruction" in e for e in plan.rows[1].errors)


async def test_unknown_country_and_university_are_errors(session: AsyncSession):
    await _seed(session)
    universities = _csv(
        "country_iso,name,city,website,timezone,logo_url,ranking",
        "FR,Sorbonne,Paris,,Europe/Paris,,",
    )
    programs = _csv(
        PROGRAMS_HEADER,
        "DE,Nowhere University,Informatics,,master,cs_it,English,2,Fall,https://x.de,,,",
    )

    plan = await _plan(session, universities=universities, programs=programs)

    assert any("country_iso" in e for e in plan.rows[0].errors)
    assert any("university_name" in e for e in plan.rows[1].errors)


async def test_new_program_requires_source_url(session: AsyncSession):
    await _seed(session)
    data = _csv(PROGRAMS_HEADER, "DE,TU Munich,Informatics,,master,cs_it,English,2,Fall,,,,")

    plan = await _plan(session, programs=data)

    assert plan.rows[0].status == STATUS_ERROR
    assert any("source_url" in e for e in plan.rows[0].errors)


async def test_duplicate_row_in_file_is_an_error(session: AsyncSession):
    await _seed(session)
    row = "DE,TU Munich,Informatics,,master,cs_it,English,2,Fall,https://x.de,,,"
    data = _csv(PROGRAMS_HEADER, row, row.replace("Informatics", "INFORMATICS"))

    plan = await _plan(session, programs=data)

    assert plan.rows[0].status == STATUS_NEW
    assert plan.rows[1].status == STATUS_ERROR


# --------------------------- bo'sh katak qoidasi ---------------------------


async def test_empty_cell_does_not_change_existing_value(session: AsyncSession):
    university = await _seed(session)
    law = (await session.execute(select(Field).where(Field.code == "law"))).scalar_one()
    session.add(Program(
        university_id=university.id, name="LLM", degree_level=DegreeLevel.MASTER,
        field_id=law.id, language_of_instruction="German", duration_years=1,
        intake_term="Winter", source_url="https://old.de", notes="Admin izohi",
        notes_en="Admin note", verified_at=datetime.now(UTC), verified_by="admin",
    ))
    await session.commit()

    # Faqat qisqartma to'ldirilgan, qolgan hamma katak bo'sh.
    data = _csv(PROGRAMS_HEADER, "DE,TU Munich,llm,LL.M.,master,,,,,,,,")
    plan = await _import(session, programs=data)

    assert plan.rows[0].status == STATUS_UPDATE
    assert set(plan.rows[0].changes) == {"abbreviation"}
    program = (await session.execute(select(Program))).scalar_one()
    assert program.abbreviation == "LL.M."
    assert program.field_id == law.id
    assert program.language_of_instruction == "German"
    assert program.source_url == "https://old.de"
    assert program.notes == "Admin izohi"
    assert program.notes_en == "Admin note"


async def test_empty_cell_does_not_change_university(session: AsyncSession):
    university = await _seed(session)
    university.website = "https://www.tum.de"
    university.ranking = 28
    await session.commit()

    data = _csv("country_iso,name,city,website,timezone,logo_url,ranking", "DE,tu munich,,,,,")
    plan = await _plan(session, universities=data)

    assert plan.rows[0].status == STATUS_UNCHANGED


# ------------------------------ takroriy import ------------------------------


async def test_importing_twice_does_not_create_duplicates(session: AsyncSession):
    await _seed(session)
    data = _csv(
        PROGRAMS_HEADER,
        "DE,TU Munich,Informatics,M.Sc.,master,cs_it,English,2,Fall,https://tum.de/i,,,",
        "DE,TU Munich,Informatics,B.Sc.,bachelor,cs_it,German,3,Fall,https://tum.de/b,,,",
    )

    await _import(session, programs=data)
    second = await _plan(session, programs=data)

    assert [r.status for r in second.rows] == [STATUS_UNCHANGED, STATUS_UNCHANGED]
    await apply_plan(session, second, admin="tester")
    await session.commit()
    assert await _count(session, Program) == 2


# ------------------------------ fayl formati ------------------------------


async def test_bom_and_semicolon_delimiter(session: AsyncSession):
    await _seed(session)
    text = (
        PROGRAMS_HEADER.replace(",", ";")
        + "\nDE;TU Munich;Informatics;;master;cs_it;English;1,5;Fall;https://tum.de/i;"
        + "Izoh, vergul bilan;;\n"
    )
    data = "﻿".encode() + text.encode("utf-8")

    plan = await _import(session, programs=data)

    assert plan.rows[0].status == STATUS_NEW
    program = (await session.execute(select(Program))).scalar_one()
    assert float(program.duration_years) == 1.5
    assert program.notes == "Izoh, vergul bilan"


def test_non_utf8_file_is_rejected():
    data = PROGRAMS_HEADER.encode() + "\nDE,Universität".encode("cp1252")
    with pytest.raises(CsvFileError, match="UTF-8"):
        parse_csv(data, "programs")


def test_unknown_column_is_rejected():
    with pytest.raises(CsvFileError, match="Noma'lum ustun"):
        parse_csv(_csv("iso_code,name_uz,capital"), "countries")


def test_missing_key_column_is_rejected():
    with pytest.raises(CsvFileError, match="Majburiy ustun"):
        parse_csv(_csv("name_uz,name_ru,name_en"), "countries")


def _many_programs(count: int) -> bytes:
    rows = [
        f"DE,TU Munich,Dastur {i},M.Sc.,master,cs_it,English,2,2027 Winter,"
        f"https://example.org/{i},,,"
        for i in range(count)
    ]
    return _csv(PROGRAMS_HEADER, *rows)


def test_file_larger_than_five_thousand_rows_is_accepted():
    # Katalog o'sgani uchun chegara ko'tarilgan: o'z eksportimizni qaytib
    # import qilib bo'lishi kerak, aks holda zaxira fayl ishlatilmaydi.
    assert len(parse_csv(_many_programs(6000), "programs")) == 6000


def test_file_over_the_row_limit_is_rejected():
    with pytest.raises(CsvFileError, match="Qatorlar soni"):
        parse_csv(_many_programs(MAX_ROWS + 1), "programs")


# ------------------------------ eksport ------------------------------


async def test_export_then_import_is_unchanged(session: AsyncSession):
    await _seed(session)
    await _import(session, programs=_csv(
        PROGRAMS_HEADER,
        "DE,TU Munich,Informatics,M.Sc.,master,cs_it,English,1.5,Fall,https://tum.de/i,a,b,c",
    ))

    exported = {
        kind: (await export_csv(session, kind)).encode("utf-8")
        for kind in ("countries", "universities", "programs")
    }
    plan = await _plan(session, **exported)

    assert not plan.has_errors
    assert {r.status for r in plan.rows} == {STATUS_UNCHANGED}


@pytest.mark.parametrize("kind", ["countries", "universities", "programs"])
def test_template_has_header_and_one_sample_row(kind):
    rows = parse_csv(template_csv(kind).encode("utf-8"), kind)
    assert len(rows) == 1


# ------------------------- tafsilot ustunlari -------------------------

DETAILS_HEADER = PROGRAMS_HEADER + (
    ",ielts_min,toefl_min,tuition_amount,tuition_currency,deadline_close,"
    "has_application_fee,application_fee_amount,application_fee_currency,"
    "has_scholarship,scholarship_url,required_documents,requirements_text"
)
BASE = "DE,TU Munich,Informatics,BSc,bachelor,cs_it,English,3,2027 September,https://tum.de/i,,,"


async def _load_program(session: AsyncSession) -> Program:
    from sqlalchemy.orm import selectinload

    session.expire_all()
    return (
        await session.execute(
            select(Program).options(
                selectinload(Program.requirement),
                selectinload(Program.cost),
                selectinload(Program.deadlines),
            )
        )
    ).scalar_one()


async def test_details_are_saved_for_new_program(session: AsyncSession):
    await _seed(session)
    data = _csv(
        DETAILS_HEADER,
        BASE + ",6.5,90,38000,gbp,2027-01-14,yes,28.95,GBP,no,,"
        "transcript|personal_statement|reference,A level: AAA|Maths A",
    )

    plan = await _import(session, programs=data)

    assert plan.rows[0].status == STATUS_NEW
    program = await _load_program(session)
    assert float(program.requirement.ielts_min) == 6.5
    assert program.requirement.toefl_min == 90
    assert float(program.cost.tuition_amount) == 38000
    assert program.cost.currency == "GBP"
    assert [d.date_utc.date().isoformat() for d in program.deadlines] == ["2027-01-14"]
    assert program.has_application_fee is True
    assert float(program.application_fee_amount) == 28.95
    assert program.has_scholarship is False
    assert program.required_documents == ["transcript", "personal_statement", "reference"]
    assert program.requirements_text == "A level: AAA\nMaths A"


async def test_empty_detail_cells_keep_existing_details(session: AsyncSession):
    await _seed(session)
    await _import(session, programs=_csv(
        DETAILS_HEADER, BASE + ",6.5,90,38000,GBP,2027-01-14,yes,28.95,GBP,,,transcript,",
    ))

    # Faqat IELTS o'zgaradi, qolgan tafsilot kataklari bo'sh.
    plan = await _plan(session, programs=_csv(
        DETAILS_HEADER, "DE,TU Munich,Informatics,,bachelor,,,,,,,,,7,,,,,,,,,,,",
    ))

    assert plan.rows[0].status == STATUS_UPDATE
    assert set(plan.rows[0].changes) == {"ielts_min"}
    await apply_plan(session, plan, admin="tester")
    await session.commit()
    program = await _load_program(session)
    assert float(program.requirement.ielts_min) == 7
    assert program.requirement.toefl_min == 90
    assert float(program.cost.tuition_amount) == 38000
    assert len(program.deadlines) == 1
    assert program.required_documents == ["transcript"]


async def test_invalid_detail_values_are_errors(session: AsyncSession):
    await _seed(session)
    rows = [
        BASE + ",6.3,,,,,,,,,,,",                       # IELTS 0.5 qadamda emas
        BASE.replace("Informatics", "A") + ",,,38000,,,,,,,,,",   # valyutasiz kontrakt
        BASE.replace("Informatics", "B") + ",,,,,14/01/2027,,,,,,,",  # sana formati
        BASE.replace("Informatics", "C") + ",,,,,,maybe,,,,,,",     # yes/no emas
        BASE.replace("Informatics", "D") + ",,,,,,,,,,,diploma,",   # noma'lum hujjat
    ]
    plan = await _plan(session, programs=_csv(DETAILS_HEADER, *rows))

    assert [r.status for r in plan.rows] == [STATUS_ERROR] * 5


async def test_export_then_import_with_details_is_unchanged(session: AsyncSession):
    await _seed(session)
    await _import(session, programs=_csv(
        DETAILS_HEADER,
        BASE + ",6.5,90,38000,GBP,2027-01-14,yes,28.95,GBP,yes,https://tum.de/s,"
        "transcript|cv,Line one|Line two",
    ))

    exported = {
        kind: (await export_csv(session, kind)).encode("utf-8")
        for kind in ("countries", "universities", "programs")
    }
    plan = await _plan(session, **exported)

    assert not plan.has_errors, [(r.line, r.errors) for r in plan.rows if r.errors]
    assert {r.status for r in plan.rows} == {STATUS_UNCHANGED}


# --------------------------------- grantlar ---------------------------------

SCHOLARSHIPS_HEADER = (
    "name,country_isos,description,description_ru,description_en,logo_url,coverage_type,"
    "coverage_percent,stipend_amount,stipend_max,stipend_period,currency,ielts_min,toefl_min,"
    "work_experience_years,degree_levels,study_language,duration_min_years,duration_max_years,"
    "selection_stages,extras_flight,extras_insurance,extras_dormitory,extras_language_course,"
    "age_limit,citizenship_eligible,university_choice,application_linked_to_program,"
    "universities_text,selected_by,requirements_text,source_url,deadline_close,intake_term"
)

SCHOLARSHIP_ROW = (
    "Chevening,GB,,,UK government scholarship,,full,,1500,,month,GBP,6.5,,2,master,English,"
    "1,1,3,yes,no,no,no,,yes,user_chooses,yes,Any UK university,"
    "Chevening Secretariat,Bachelor degree|Two years of work experience,"
    "https://www.chevening.org/,2027-11-02,2027 Autumn"
)


async def _seed_gb(session: AsyncSession) -> None:
    session.add(
        Country(name_uz="Buyuk Britaniya", name_ru="Великобритания", name_en="UK", iso_code="GB")
    )
    await session.commit()


@pytest.mark.anyio
async def test_scholarship_is_created_with_all_details(session: AsyncSession) -> None:
    await _seed_gb(session)
    await _import(session, scholarships=_csv(SCHOLARSHIPS_HEADER, SCHOLARSHIP_ROW))

    item = (
        await session.execute(
            select(Scholarship).where(Scholarship.name == "Chevening")
        )
    ).scalar_one()
    await session.refresh(item, ["countries", "deadlines"])

    assert item.coverage_type is CoverageType.FULL
    assert item.university_choice is UniversityChoiceType.USER_CHOOSES
    assert float(item.stipend_amount) == 1500
    assert item.stipend_period == "month"
    assert item.currency == "GBP"
    assert float(item.ielts_min) == 6.5
    assert item.work_experience_years == 2
    assert item.degree_levels == ["master"]
    assert item.study_language == "English"
    assert item.selection_stages == 3
    assert item.extras_flight is True
    assert item.extras_insurance is False
    assert item.citizenship_eligible is True
    assert item.selected_by == "Chevening Secretariat"
    assert item.universities_text == "Any UK university"
    # `|` bilan ajratilgan talablar bazada alohida qatorlarga aylanadi.
    assert item.requirements_text == "Bachelor degree\nTwo years of work experience"
    assert [c.iso_code for c in item.countries] == ["GB"]
    assert [d.date_utc.date().isoformat() for d in item.deadlines] == ["2027-11-02"]
    assert item.verified_by == "tester"


@pytest.mark.anyio
async def test_scholarship_empty_cells_keep_existing_values(session: AsyncSession) -> None:
    await _seed_gb(session)
    await _import(session, scholarships=_csv(SCHOLARSHIPS_HEADER, SCHOLARSHIP_ROW))

    # Faqat nom va bitta katak — qolgan hamma narsa o'z joyida qolishi kerak.
    bare = "Chevening," + "," * 31 + ","
    minimal = bare[: bare.index(",") + 1] + "," * 7 + "1700" + "," * 25
    plan = await _plan(session, scholarships=_csv(SCHOLARSHIPS_HEADER, minimal))
    assert [r.status for r in plan.rows] == [STATUS_UPDATE]
    await apply_plan(session, plan, admin="tester")
    await session.commit()

    item = (
        await session.execute(select(Scholarship).where(Scholarship.name == "Chevening"))
    ).scalar_one()
    await session.refresh(item, ["countries"])
    assert float(item.stipend_amount) == 1700
    # Bo'sh kataklar hech narsani o'chirmadi:
    assert item.study_language == "English"
    assert item.selected_by == "Chevening Secretariat"
    assert [c.iso_code for c in item.countries] == ["GB"]


@pytest.mark.anyio
async def test_scholarship_export_then_import_is_unchanged(session: AsyncSession) -> None:
    await _seed_gb(session)
    await _import(session, scholarships=_csv(SCHOLARSHIPS_HEADER, SCHOLARSHIP_ROW))

    exported = await export_csv(session, "scholarships")
    plan = await _plan(session, scholarships=exported.encode("utf-8"))
    assert [r.status for r in plan.rows] == [STATUS_UNCHANGED]


@pytest.mark.anyio
async def test_scholarship_invalid_values_are_errors(session: AsyncSession) -> None:
    await _seed_gb(session)
    bad = SCHOLARSHIP_ROW.replace(",full,", ",everything,").replace(",6.5,", ",6.3,")
    plan = await _plan(session, scholarships=_csv(SCHOLARSHIPS_HEADER, bad))
    assert [r.status for r in plan.rows] == [STATUS_ERROR]
    messages = " ".join(plan.rows[0].errors)
    assert "coverage_type" in messages
    assert "ielts_min" in messages


@pytest.mark.anyio
async def test_scholarship_unknown_country_is_an_error(session: AsyncSession) -> None:
    plan = await _plan(
        session, scholarships=_csv(SCHOLARSHIPS_HEADER, SCHOLARSHIP_ROW)
    )
    assert [r.status for r in plan.rows] == [STATUS_ERROR]
    assert "country_isos" in " ".join(plan.rows[0].errors)


@pytest.mark.anyio
async def test_scholarship_template_is_importable(session: AsyncSession) -> None:
    """Shablon namunasi darhol import bo'lishi kerak (davlati bazada bo'lsa)."""
    await _seed_gb(session)
    plan = await _plan(session, scholarships=template_csv("scholarships").encode("utf-8"))
    assert [r.status for r in plan.rows] == [STATUS_NEW], [r.errors for r in plan.rows]
