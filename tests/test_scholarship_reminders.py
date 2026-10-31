"""Hukumat granti muddatiga 30 kun qolganda bot eslatmasi."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CoverageType,
    DeadlineType,
    DegreeLevel,
    Scholarship,
    ScholarshipDeadline,
    ScholarshipNotificationLog,
    UniversityChoiceType,
    User,
)
from app.services.scholarship_reminder_service import run_scholarship_reminder_scan

pytestmark = pytest.mark.asyncio

TODAY = date(2027, 3, 10)


async def _scholarship(
    session: AsyncSession, *, close_in_days: int, name: str = "DAAD", levels: list | None = None
) -> Scholarship:
    scholarship = Scholarship(
        name=name,
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        degree_levels=levels,
        source_url="https://example.com",
        verified_at=datetime.now(UTC),
        verified_by="tester",
    )
    session.add(scholarship)
    await session.flush()
    # 12:00 UTC — Toshkentda ham o'sha kun.
    close = datetime.combine(TODAY + timedelta(days=close_in_days), datetime.min.time(), UTC)
    session.add(
        ScholarshipDeadline(
            scholarship_id=scholarship.id,
            type=DeadlineType.APPLICATION_CLOSE,
            date_utc=close + timedelta(hours=12),
            intake_term="2027",
        )
    )
    await session.commit()
    return scholarship


async def _user(session: AsyncSession, telegram_id: int = 700100, **kwargs) -> User:
    user = User(telegram_id=telegram_id, **kwargs)
    session.add(user)
    await session.commit()
    return user


async def test_sends_once_when_30_days_left(session: AsyncSession):
    await _scholarship(session, close_in_days=30)
    user = await _user(session)
    bot = AsyncMock()

    result = await run_scholarship_reminder_scan(bot, session, today=TODAY)

    assert result.sent_users == 1
    bot.send_message.assert_awaited_once()
    assert bot.send_message.await_args.args[0] == user.telegram_id
    assert "DAAD" in bot.send_message.await_args.args[1]

    # Ertasi kuni (29 kun) — qayta yuborilmaydi.
    again = await run_scholarship_reminder_scan(bot, session, today=TODAY + timedelta(days=1))
    assert again.sent_users == 0
    assert bot.send_message.await_count == 1
    logs = (await session.execute(select(ScholarshipNotificationLog))).scalars().all()
    assert len(logs) == 1


@pytest.mark.parametrize("days", [31, 27, 5])
async def test_not_sent_outside_window(session: AsyncSession, days: int):
    await _scholarship(session, close_in_days=days)
    await _user(session)

    result = await run_scholarship_reminder_scan(None, session, today=TODAY, dry_run=True)

    assert result.due == []
    assert result.sent_users == 0


async def test_missed_day_is_caught_up(session: AsyncSession):
    await _scholarship(session, close_in_days=28)
    await _user(session)

    result = await run_scholarship_reminder_scan(None, session, today=TODAY, dry_run=True)

    assert result.sent_users == 1


async def test_skips_muted_blocked_and_other_degree(session: AsyncSession):
    await _scholarship(session, close_in_days=30, levels=["bachelor"])
    await _user(session, telegram_id=1, notifications_enabled=False)
    await _user(session, telegram_id=2, is_blocked=True)
    await _user(session, telegram_id=3, degree_level=DegreeLevel.MASTER)
    await _user(session, telegram_id=4, degree_level=DegreeLevel.BACHELOR)
    await _user(session, telegram_id=5)  # daraja tanlanmagan — yuboriladi
    bot = AsyncMock()

    result = await run_scholarship_reminder_scan(bot, session, today=TODAY)

    assert result.sent_users == 2
    assert sorted(call.args[0] for call in bot.send_message.await_args_list) == [4, 5]


async def test_several_grants_in_one_message(session: AsyncSession):
    await _scholarship(session, close_in_days=30, name="DAAD")
    await _scholarship(session, close_in_days=29, name="Chevening")
    await _user(session)
    bot = AsyncMock()

    await run_scholarship_reminder_scan(bot, session, today=TODAY)

    bot.send_message.assert_awaited_once()
    text = bot.send_message.await_args.args[1]
    assert "DAAD" in text and "Chevening" in text
