"""Deadline eslatmalari mantig'i.

"Bugun" har joyda PARAMETR — testlar haqiqiy kalendarga bog'liq emas va
yil oxiri / kabisa yili kabi holatlarni ham tekshirib bo'ladi.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Country,
    Deadline,
    DeadlineType,
    DegreeLevel,
    NotificationLog,
    NotificationType,
    Program,
    SavedProgram,
    SavedProgramStatus,
    University,
    User,
)
from app.services.reminder_service import (
    DeadlinePrecision,
    build_digest,
    collect_due,
    next_month_occurrence,
    plan_for_saved,
    resolve_deadline,
    run_reminder_scan,
    send_immediate_if_due,
)

pytestmark = pytest.mark.asyncio

TODAY = date(2027, 3, 10)


async def _program(
    session: AsyncSession,
    *,
    close_in_days: int | None = None,
    deadline_month: int | None = None,
    name: str = "Computer Science",
) -> Program:
    # Davlat bitta testda bir necha marta kerak bo'lishi mumkin (jamlangan
    # xabar sinovida ikkita dastur bor), `iso_code` esa unique — shuning
    # uchun bor bo'lsa qayta ishlatiladi.
    country = (
        await session.execute(select(Country).where(Country.iso_code == "TR"))
    ).scalar_one_or_none()
    if country is None:
        country = Country(
            name_uz="Turkiya", name_ru="Turtsiya", name_en="Turkey", iso_code="TR"
        )
        session.add(country)
        await session.flush()

    university = University(
        country_id=country.id, name=f"Test University ({name})", city="Istanbul", timezone="UTC"
    )
    session.add(university)
    await session.flush()

    program = Program(
        university_id=university.id,
        name=name,
        degree_level=DegreeLevel.BACHELOR,
        language_of_instruction="English",
        duration_years=4,
        intake_term="2027 Fall",
        source_url="https://example.com",
        verified_at=datetime.now(UTC),
        verified_by="tester",
        deadline_month=deadline_month,
    )
    session.add(program)
    await session.flush()

    if close_in_days is not None:
        close_date = TODAY + timedelta(days=close_in_days)
        session.add(
            Deadline(
                program_id=program.id,
                type=DeadlineType.APPLICATION_CLOSE,
                # Toshkent kuni muhim: 12:00 UTC har qanday mintaqada ham
                # o'sha kunga tushadi.
                date_utc=datetime(close_date.year, close_date.month, close_date.day, 12, tzinfo=UTC),
                intake_term="2027 Fall",
            )
        )
    await session.flush()
    return program


async def _user(session: AsyncSession, *, telegram_id: int = 500100, **kwargs) -> User:
    user = User(telegram_id=telegram_id, username=f"u{telegram_id}", **kwargs)
    session.add(user)
    await session.flush()
    return user


async def _save(
    session: AsyncSession,
    user: User,
    program: Program,
    *,
    saved_days_ago: int = 0,
    **kwargs,
) -> SavedProgram:
    saved = SavedProgram(user_id=user.id, program_id=program.id, **kwargs)
    session.add(saved)
    await session.flush()
    saved.created_at = datetime(
        TODAY.year, TODAY.month, TODAY.day, 9, tzinfo=UTC
    ) - timedelta(days=saved_days_ago)
    await session.flush()
    await session.refresh(saved, attribute_names=["program", "user"])
    await session.refresh(saved.program, attribute_names=["deadlines", "university"])
    return saved


# ------------------------------------------------------------- aniqlik --


async def test_precision_exact_comes_from_deadlines_table(session: AsyncSession):
    """Aniq sana `deadlines` jadvalidan olinadi, `programs` dan emas."""
    program = await _program(session, close_in_days=30)
    await session.refresh(program, attribute_names=["deadlines"])

    info = resolve_deadline(program)

    assert info.precision is DeadlinePrecision.EXACT
    assert info.exact_date == TODAY + timedelta(days=30)


async def test_precision_month_when_only_month_known(session: AsyncSession):
    program = await _program(session, deadline_month=1)
    await session.refresh(program, attribute_names=["deadlines"])

    info = resolve_deadline(program)

    assert info.precision is DeadlinePrecision.MONTH
    assert info.month == 1


async def test_precision_unknown_without_any_date(session: AsyncSession):
    program = await _program(session)
    await session.refresh(program, attribute_names=["deadlines"])

    assert resolve_deadline(program).precision is DeadlinePrecision.UNKNOWN


# ------------------------------------------------------- oy chegaralari --


async def test_month_occurrence_stays_in_current_year_until_month_ends():
    # 20-dekabr: dekabr hali tugamagan, shuning uchun shu yilning dekabri.
    assert next_month_occurrence(12, date(2026, 12, 20)) == date(2026, 12, 1)


async def test_month_occurrence_rolls_over_to_next_year():
    # 20-dekabrda yanvar — keyingi yilniki.
    assert next_month_occurrence(1, date(2026, 12, 20)) == date(2027, 1, 1)


async def test_month_occurrence_past_month_goes_to_next_year():
    assert next_month_occurrence(3, date(2026, 5, 1)) == date(2027, 3, 1)


# ------------------------------------------------- rejalashtirish: exact --


async def test_exact_14d_due_exactly_on_day(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, close_in_days=14)
    saved = await _save(session, user, program)

    plans = plan_for_saved(saved, TODAY)

    assert [p.notif_type for p in plans] == [NotificationType.EXACT_14D]


async def test_exact_3d_adds_second_message(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, close_in_days=3)
    saved = await _save(session, user, program)

    plans = plan_for_saved(saved, TODAY)

    # 14 kunligi ham "vaqti kelgan" (o'tib ketgan), 3 kunligi ham — ikkalasi.
    assert {p.notif_type for p in plans} == {
        NotificationType.EXACT_14D,
        NotificationType.EXACT_3D,
    }


async def test_nothing_planned_long_before_deadline(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, close_in_days=90)
    saved = await _save(session, user, program)

    assert plan_for_saved(saved, TODAY) == []


async def test_passed_deadline_produces_nothing(session: AsyncSession):
    """Muddati o'tgan dastur "yopilgan" — xabar yuborilmaydi."""
    user = await _user(session)
    program = await _program(session, close_in_days=-1)
    saved = await _save(session, user, program)

    assert plan_for_saved(saved, TODAY) == []


async def test_catch_up_sends_missed_day(session: AsyncSession):
    """Server bir kun o'chiq tursa, xabar keyingi kuni baribir ketadi."""
    user = await _user(session)
    program = await _program(session, close_in_days=12)
    saved = await _save(session, user, program)

    plans = plan_for_saved(saved, TODAY)

    # 14 kunlik xabar sanasi ikki kun oldin edi — baribir rejalashtiriladi.
    assert [p.notif_type for p in plans] == [NotificationType.EXACT_14D]
    assert plans[0].due_on == TODAY - timedelta(days=2)


# -------------------------------------------------- rejalashtirish: month --


async def test_month_before_fires_on_first_of_previous_month(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, deadline_month=4)
    saved = await _save(session, user, program)

    # Bugun 10-mart: aprel uchun "oldingi oy boshi" 1-mart — vaqti kelgan.
    plans = plan_for_saved(saved, TODAY)

    assert [p.notif_type for p in plans] == [NotificationType.MONTH_BEFORE]


async def test_month_start_fires_within_the_month(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, deadline_month=3)
    saved = await _save(session, user, program)

    plans = plan_for_saved(saved, TODAY)

    assert {p.notif_type for p in plans} == {
        NotificationType.MONTH_BEFORE,
        NotificationType.MONTH_START,
    }


# ------------------------------------------------ rejalashtirish: unknown --


async def test_unknown_check_after_three_days(session: AsyncSession):
    user = await _user(session)
    program = await _program(session)
    saved = await _save(session, user, program, saved_days_ago=3)

    plans = plan_for_saved(saved, TODAY)

    assert [p.notif_type for p in plans] == [NotificationType.UNKNOWN_CHECK]


async def test_unknown_check_not_before_three_days(session: AsyncSession):
    user = await _user(session)
    program = await _program(session)
    saved = await _save(session, user, program, saved_days_ago=2)

    assert plan_for_saved(saved, TODAY) == []


# ------------------------------------------------------------- tanlash --


async def test_duplicate_is_not_sent_twice(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, close_in_days=14)
    await _save(session, user, program)
    session.add(
        NotificationLog(
            user_id=user.id, program_id=program.id, notif_type=NotificationType.EXACT_14D
        )
    )
    await session.flush()

    assert await collect_due(session, TODAY) == []


async def test_muted_program_is_skipped(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, close_in_days=14)
    await _save(session, user, program, reminders_active=False)

    assert await collect_due(session, TODAY) == []


async def test_applied_program_is_skipped(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, close_in_days=14)
    await _save(session, user, program, status=SavedProgramStatus.APPLIED)

    assert await collect_due(session, TODAY) == []


async def test_notifications_disabled_blocks_everything(session: AsyncSession):
    user = await _user(session, notifications_enabled=False)
    program = await _program(session, close_in_days=14)
    await _save(session, user, program)

    assert await collect_due(session, TODAY) == []


async def test_blocked_user_is_skipped(session: AsyncSession):
    user = await _user(session, is_blocked=True)
    program = await _program(session, close_in_days=14)
    await _save(session, user, program)

    assert await collect_due(session, TODAY) == []


async def test_messages_missed_while_disabled_are_not_resent(session: AsyncSession):
    """Qayta yoqilganda o'tib ketgan xabarlar orqaga qarab yuborilmaydi."""
    user = await _user(
        session,
        notifications_enabled=True,
        # Bugun yoqilgan, 14 kunlik xabar sanasi esa ikki kun oldin edi.
        notifications_enabled_at=datetime(TODAY.year, TODAY.month, TODAY.day, 8, tzinfo=UTC),
    )
    program = await _program(session, close_in_days=12)
    await _save(session, user, program)

    assert await collect_due(session, TODAY) == []


async def test_message_due_after_enabling_is_sent(session: AsyncSession):
    user = await _user(
        session,
        notifications_enabled_at=datetime(TODAY.year, TODAY.month, 1, 8, tzinfo=UTC),
    )
    program = await _program(session, close_in_days=14)
    await _save(session, user, program)

    due = await collect_due(session, TODAY)

    assert [p.notif_type for p in due] == [NotificationType.EXACT_14D]


# ------------------------------------------------------- jamlangan xabar --


async def test_one_digest_for_several_programs(session: AsyncSession):
    user = await _user(session)
    first = await _program(session, close_in_days=14, name="Dastur A")
    second = await _program(session, close_in_days=3, name="Dastur B")
    await _save(session, user, first)
    await _save(session, user, second)

    due = await collect_due(session, TODAY)
    text, markup = build_digest(due, "uz")

    assert len(due) == 3  # A: 14d; B: 14d + 3d
    assert "Dastur A" in text and "Dastur B" in text
    # Har bir dastur uchun o'z tugmalari bo'lishi kerak.
    callbacks = [
        b.callback_data for row in markup.inline_keyboard for b in row if b.callback_data
    ]
    assert f"applied:{first.id}" in callbacks
    assert f"applied:{second.id}" in callbacks


async def test_scan_writes_log_and_does_not_repeat(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, close_in_days=14)
    await _save(session, user, program)

    first = await run_reminder_scan(None, session, today=TODAY, dry_run=True)
    assert first.sent_messages == 1

    # dry_run yozmaydi — shuning uchun ikkinchi marta ham topiladi.
    again = await run_reminder_scan(None, session, today=TODAY, dry_run=True)
    assert again.sent_messages == 1


# -------------------------------------------- saqlash paytidagi darhol xabar --


async def test_immediate_when_deadline_is_very_close(session: AsyncSession):
    """3 kundan kam: darhol yuboriladi, ikkala rejalashtirilgani ham yopiladi."""
    user = await _user(session)
    program = await _program(session, close_in_days=2)
    saved = await _save(session, user, program)

    sent = await send_immediate_if_due(None, session, saved, today=TODAY)

    assert sent is NotificationType.EXACT_IMMEDIATE
    assert await collect_due(session, TODAY) == []


async def test_immediate_keeps_three_day_reminder(session: AsyncSession):
    """3-14 kun: darhol yuboriladi, lekin 3 kunlik eslatma o'z vaqtida ketadi."""
    user = await _user(session)
    program = await _program(session, close_in_days=10)
    saved = await _save(session, user, program)

    sent = await send_immediate_if_due(None, session, saved, today=TODAY)
    assert sent is NotificationType.EXACT_IMMEDIATE

    # Bugun 3 kunlikning vaqti emas, lekin deadline kuniga 3 kun qolganda keladi.
    later = TODAY + timedelta(days=7)
    due = await collect_due(session, later)
    assert [p.notif_type for p in due] == [NotificationType.EXACT_3D]


async def test_no_immediate_when_deadline_is_far(session: AsyncSession):
    user = await _user(session)
    program = await _program(session, close_in_days=40)
    saved = await _save(session, user, program)

    assert await send_immediate_if_due(None, session, saved, today=TODAY) is None


async def test_no_immediate_when_notifications_disabled(session: AsyncSession):
    user = await _user(session, notifications_enabled=False)
    program = await _program(session, close_in_days=2)
    saved = await _save(session, user, program)

    assert await send_immediate_if_due(None, session, saved, today=TODAY) is None
