from datetime import UTC, datetime, timedelta

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Country,
    Deadline,
    DeadlineType,
    DegreeLevel,
    Program,
    SavedProgram,
    SavedProgramStatus,
    University,
    User,
)
from app.services.reminder_service import (
    find_due_reminders,
    is_already_sent,
    mark_sent,
    run_reminder_scan,
)

pytestmark = pytest.mark.asyncio


async def _make_saved_program(session: AsyncSession, *, days_until_deadline: int, reminders_active: bool = True) -> SavedProgram:
    country = Country(name_uz="Turkiya", name_ru="Turkiya", name_en="Turkey", iso_code="TR")
    session.add(country)
    await session.flush()

    university = University(country_id=country.id, name="Test University", city="Istanbul", timezone="UTC")
    session.add(university)
    await session.flush()

    program = Program(
        university_id=university.id,
        name="Computer Science",
        degree_level=DegreeLevel.BACHELOR,
        language_of_instruction="English",
        duration_years=4,
        intake_term="2026 Fall",
        source_url="https://example.com",
        verified_at=datetime.now(UTC),
        verified_by="tester",
    )
    session.add(program)
    await session.flush()

    deadline = Deadline(
        program_id=program.id,
        type=DeadlineType.APPLICATION_CLOSE,
        date_utc=datetime.now(UTC) + timedelta(days=days_until_deadline),
        intake_term="2026 Fall",
    )
    session.add(deadline)

    user = User(telegram_id=42)
    session.add(user)
    await session.flush()

    saved = SavedProgram(
        user_id=user.id,
        program_id=program.id,
        status=SavedProgramStatus.PLANNING,
        reminders_active=reminders_active,
    )
    session.add(saved)
    await session.commit()

    await session.refresh(saved, attribute_names=["program", "user"])
    await session.refresh(saved.program, attribute_names=["deadlines", "university"])
    return saved


async def test_finds_reminder_at_threshold_day(session: AsyncSession):
    await _make_saved_program(session, days_until_deadline=30)

    due = await find_due_reminders(session)

    assert len(due) == 1
    assert due[0].days_left == 30


async def test_no_reminder_outside_thresholds(session: AsyncSession):
    await _make_saved_program(session, days_until_deadline=25)

    due = await find_due_reminders(session)

    assert due == []


async def test_no_reminder_when_reminders_inactive(session: AsyncSession):
    await _make_saved_program(session, days_until_deadline=7, reminders_active=False)

    due = await find_due_reminders(session)

    assert due == []


async def test_dedup_prevents_resending():
    redis = FakeAsyncRedis()
    from app.services.reminder_service import DueReminder

    class _Fake:
        id = 1

    reminder = DueReminder(saved_program=_Fake(), deadline=_Fake(), days_left=7)

    assert await is_already_sent(redis, reminder) is False
    await mark_sent(redis, reminder)
    assert await is_already_sent(redis, reminder) is True


async def test_run_reminder_scan_sends_and_dedupes(session: AsyncSession):
    await _make_saved_program(session, days_until_deadline=14)
    redis = FakeAsyncRedis()

    sent_messages = []

    class FakeBot:
        async def send_message(self, chat_id, text, reply_markup=None):
            sent_messages.append((chat_id, text))

    bot = FakeBot()

    first_run_count = await run_reminder_scan(bot, session, redis)
    second_run_count = await run_reminder_scan(bot, session, redis)

    assert first_run_count == 1
    assert second_run_count == 0
    assert len(sent_messages) == 1
