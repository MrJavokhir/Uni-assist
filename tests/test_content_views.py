"""Dastur va grant sahifalarini ko'rishlar soni."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.db.models import (
    Country,
    CoverageType,
    DegreeLevel,
    Program,
    Scholarship,
    University,
    UniversityChoiceType,
    User,
)
from app.services import view_service
from app.services.view_service import VIEW_GRANT, VIEW_PROGRAM
from app.webapp import api

NOW = datetime(2026, 11, 4, 12, tzinfo=UTC)


async def _users(session, count: int = 2) -> list[User]:
    users = [User(telegram_id=7000 + i) for i in range(count)]
    session.add_all(users)
    await session.commit()
    return users


async def test_same_user_counts_once_a_day(session) -> None:
    [user, _] = await _users(session)

    assert await view_service.record(session, user, VIEW_PROGRAM, 1, NOW) == 1
    assert await view_service.record(session, user, VIEW_PROGRAM, 1, NOW) == 1
    next_day = NOW + timedelta(days=1)
    assert await view_service.record(session, user, VIEW_PROGRAM, 1, next_day) == 2


async def test_each_user_and_page_counts_separately(session) -> None:
    [first, second] = await _users(session)

    await view_service.record(session, first, VIEW_PROGRAM, 1, NOW)
    assert await view_service.record(session, second, VIEW_PROGRAM, 1, NOW) == 2
    # Bir xil raqamli grant dastur hisobiga qo'shilmaydi.
    assert await view_service.record(session, first, VIEW_GRANT, 1, NOW) == 1
    assert await view_service.record(session, first, VIEW_PROGRAM, 2, NOW) == 1
    assert await view_service.counts_for(session, VIEW_PROGRAM) == {1: 2, 2: 1}


async def test_day_follows_tashkent_time(session) -> None:
    [user, _] = await _users(session)
    before_midnight = datetime(2026, 11, 4, 18, 30, tzinfo=UTC)  # Toshkentda 23:30
    after_midnight = datetime(2026, 11, 4, 19, 30, tzinfo=UTC)  # Toshkentda 00:30

    await view_service.record(session, user, VIEW_GRANT, 1, before_midnight)

    assert await view_service.record(session, user, VIEW_GRANT, 1, after_midnight) == 2


async def test_top_lists_most_viewed_first_and_skip_deleted(session) -> None:
    [first, second] = await _users(session)
    country = Country(iso_code="DE", name_uz="Germaniya", name_ru="Германия", name_en="Germany")
    session.add(country)
    await session.flush()
    university = University(country_id=country.id, name="TUM", city="Munich", timezone="UTC")
    session.add(university)
    await session.flush()
    verified = {"source_url": "https://example.com", "verified_at": NOW, "verified_by": "tester"}
    programs = [
        Program(
            university_id=university.id,
            name=name,
            degree_level=DegreeLevel.MASTER,
            language_of_instruction="English",
            duration_years=2,
            intake_term="2027 Fall",
            **verified,
        )
        for name in ("Quiet", "Popular")
    ]
    grant = Scholarship(
        name="DAAD",
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        **verified,
    )
    session.add_all([*programs, grant])
    await session.commit()

    await view_service.record(session, first, VIEW_PROGRAM, programs[0].id, NOW)
    await view_service.record(session, first, VIEW_PROGRAM, programs[1].id, NOW)
    await view_service.record(session, second, VIEW_PROGRAM, programs[1].id, NOW)
    await view_service.record(session, first, VIEW_PROGRAM, 999999, NOW)
    await view_service.record(session, first, VIEW_GRANT, grant.id, NOW)

    top = await view_service.top_programs(session, 10)
    assert [(item.name, item.detail, item.views) for item in top] == [
        ("Popular", "TUM", 2),
        ("Quiet", "TUM", 1),
    ]
    grants = await view_service.top_grants(session, 10)
    assert [(item.name, item.views) for item in grants] == [("DAAD", 1)]


async def test_totals_split_today(session) -> None:
    [user, _] = await _users(session)
    await view_service.record(session, user, VIEW_PROGRAM, 1, NOW - timedelta(days=2))
    await view_service.record(session, user, VIEW_PROGRAM, 2, NOW)

    assert await view_service.totals(session, VIEW_PROGRAM, NOW) == (2, 1)
    assert await view_service.totals(session, VIEW_GRANT, NOW) == (0, 0)


@pytest.mark.parametrize("handler", [api.view_program, api.view_scholarship], ids=["program", "grant"])
async def test_view_of_missing_page_is_404(session, handler) -> None:
    [user, _] = await _users(session)

    with pytest.raises(HTTPException) as exc:
        await handler(999999, user=user, session=session)

    assert exc.value.status_code == 404
    assert await view_service.counts_for(session, VIEW_PROGRAM) == {}
    assert await view_service.counts_for(session, VIEW_GRANT) == {}
