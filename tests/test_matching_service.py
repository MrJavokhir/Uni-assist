from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Country,
    Deadline,
    DeadlineType,
    DegreeLevel,
    GpaScale,
    LanguageCertType,
    Program,
    ProgramRequirement,
    University,
    User,
    UserLanguageCertificate,
)
from app.services.matching_service import MatchLevel, find_matches

pytestmark = pytest.mark.asyncio


async def _make_program(
    session: AsyncSession,
    *,
    country_name: str = "Turkiya",
    gpa_min: float | None = 70,
    gpa_scale: GpaScale | None = GpaScale.SCALE_100,
    ielts_min: float | None = 6.0,
    age_limit: int | None = None,
    deadline_close: datetime | None = None,
) -> Program:
    country = Country(name_uz=country_name, name_ru=country_name, name_en=country_name, iso_code="TR")
    session.add(country)
    await session.flush()

    university = University(country_id=country.id, name="Test University", city="Istanbul", timezone="UTC")
    session.add(university)
    await session.flush()

    program = Program(
        university_id=university.id,
        name="Computer Science",
        degree_level=DegreeLevel.BACHELOR,
        field_of_study="Computer Science",
        language_of_instruction="English",
        duration_years=4,
        intake_term="2026 Fall",
        source_url="https://example.com",
        verified_at=datetime.now(UTC),
        verified_by="tester",
    )
    session.add(program)
    await session.flush()

    requirement = ProgramRequirement(
        program_id=program.id,
        gpa_min=gpa_min,
        gpa_scale=gpa_scale,
        ielts_min=ielts_min,
        age_limit=age_limit,
    )
    session.add(requirement)

    if deadline_close is not None:
        session.add(
            Deadline(
                program_id=program.id,
                type=DeadlineType.APPLICATION_CLOSE,
                date_utc=deadline_close,
                intake_term="2026 Fall",
            )
        )

    await session.commit()
    await session.refresh(program, attribute_names=["requirement", "deadlines", "university"])
    return program


async def _make_user(
    session: AsyncSession,
    *,
    gpa_raw: float | None = 85,
    gpa_scale: GpaScale | None = GpaScale.SCALE_100,
    ielts_score: float | None = 6.5,
    age: int | None = None,
) -> User:
    user = User(telegram_id=1, gpa_raw=gpa_raw, gpa_scale=gpa_scale, age=age)
    session.add(user)
    await session.flush()

    if ielts_score is not None:
        session.add(
            UserLanguageCertificate(
                user_id=user.id,
                type=LanguageCertType.IELTS,
                score=ielts_score,
                exam_date=datetime.now(UTC).date(),
            )
        )
    await session.commit()
    await session.refresh(user, attribute_names=["target_countries", "language_certificates", "other_tests"])
    return user


async def test_green_when_all_requirements_met(session: AsyncSession):
    await _make_program(session, gpa_min=70, ielts_min=6.0)
    user = await _make_user(session, gpa_raw=85, ielts_score=6.5)

    results = await find_matches(session, user)

    assert len(results) == 1
    assert results[0].level == MatchLevel.GREEN
    assert results[0].missing == []


async def test_yellow_when_gpa_below_minimum(session: AsyncSession):
    await _make_program(session, gpa_min=90, ielts_min=6.0)
    user = await _make_user(session, gpa_raw=75, ielts_score=6.5)

    results = await find_matches(session, user)

    assert results[0].level == MatchLevel.YELLOW
    assert "gpa" in results[0].missing


async def test_yellow_when_no_language_certificate(session: AsyncSession):
    await _make_program(session, gpa_min=70, ielts_min=6.0)
    user = await _make_user(session, gpa_raw=85, ielts_score=None)

    results = await find_matches(session, user)

    assert results[0].level == MatchLevel.YELLOW
    assert "ielts" in results[0].missing


async def test_red_when_deadline_passed(session: AsyncSession):
    await _make_program(
        session, gpa_min=70, ielts_min=6.0, deadline_close=datetime.now(UTC) - timedelta(days=1)
    )
    user = await _make_user(session, gpa_raw=85, ielts_score=6.5)

    results = await find_matches(session, user)

    assert results[0].level == MatchLevel.RED
    assert "deadline" in results[0].missing


async def test_red_when_over_age_limit(session: AsyncSession):
    await _make_program(session, gpa_min=70, ielts_min=6.0, age_limit=30)
    user = await _make_user(session, gpa_raw=85, ielts_score=6.5, age=35)

    results = await find_matches(session, user)

    assert results[0].level == MatchLevel.RED
    assert "age" in results[0].missing


async def test_country_filter_excludes_other_countries(session: AsyncSession):
    program_tr = await _make_program(session, country_name="Turkiya")
    await session.refresh(program_tr.university, attribute_names=["country"])

    user = await _make_user(session, gpa_raw=85, ielts_score=6.5)
    user.target_countries = [program_tr.university.country]
    await session.commit()

    # Boshqa davlatdagi dastur qo'shamiz — filtrga tushmasligi kerak.
    other_country = Country(name_uz="Koreya", name_ru="Koreya", name_en="Korea", iso_code="KR")
    session.add(other_country)
    await session.flush()
    other_uni = University(country_id=other_country.id, name="Other Uni", city="Seoul", timezone="UTC")
    session.add(other_uni)
    await session.commit()

    results = await find_matches(session, user)

    assert len(results) == 1
    assert results[0].program.id == program_tr.id
