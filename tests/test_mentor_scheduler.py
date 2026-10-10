"""Mentor savollari bo'yicha davriy tekshiruv: 12 / 24 / 48 / 72 soat.

Vaqt `now` bilan oldinga suriladi — haqiqiy kutish yo'q.
"""

from datetime import timedelta

import pytest

from app.db.models import MentorQuestionStatus
from app.services import mentor_group, mentor_service
from app.services.mentor_scheduler import run_mentor_scan
from tests.mentor_fakes import (
    ANSWER_TEXT,
    GROUP_ID,
    FakeBot,
    add_country,
    add_user,
    make_question,
)

MENTOR = 7001
ADMIN = 999


async def _posted(session, bot):
    user = await add_user(session)
    await add_country(session)
    question = await make_question(session, user)
    await mentor_group.post_question(bot, session, question)
    await session.commit()
    return user, question


async def _claim(session, bot, question, now=None):
    question = await mentor_service.claim(
        session, question.id, mentor_tg_id=MENTOR, mentor_name="Ali", now=now
    )
    await mentor_group.after_claim(
        bot, session, question, mentor_tg_id=MENTOR, mentor_name="Ali", mentor_username=None
    )
    await session.commit()
    return question


async def _reload(session, question):
    return await mentor_service.get_question(session, question.id)


@pytest.mark.asyncio
async def test_claim_released_after_12_hours(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member"})
    _, question = await _posted(session, bot)
    question = await _claim(session, bot, question)
    force_id = question.force_reply_message_id
    now = question.claimed_at

    result = await run_mentor_scan(bot, session, now + timedelta(hours=11))
    assert result.released == 0

    result = await run_mentor_scan(bot, session, now + timedelta(hours=12, minutes=1))
    fresh = await _reload(session, question)
    assert result.released == 1
    assert fresh.status == MentorQuestionStatus.OPEN and fresh.claimed_by_tg_id is None
    assert force_id in bot.deleted  # eski ForceReply o'chirildi
    assert bot.has_claim_button(bot.edits[-1]["reply_markup"])  # tugma qaytdi


@pytest.mark.asyncio
async def test_24h_reminder_once_to_topic_and_admin(session, mentor_settings) -> None:
    bot = FakeBot()
    _, question = await _posted(session, bot)
    later = question.created_at + timedelta(hours=24, minutes=5)

    first = await run_mentor_scan(bot, session, later)
    second = await run_mentor_scan(bot, session, later + timedelta(minutes=30))

    assert first.reminded == 1 and second.reminded == 0
    reminders = [s for s in bot.to_chat(GROUP_ID) if "hali javobsiz" in s.text]
    assert len(reminders) == 1 and reminders[0].reply_to == question.group_message_id
    assert len(bot.to_chat(ADMIN)) == 1
    fresh = await _reload(session, question)
    assert fresh.reminder_24h_sent and fresh.admin_notified


@pytest.mark.asyncio
async def test_48h_user_notice_once_and_not_counted_towards_limit(session, mentor_settings) -> None:
    bot = FakeBot()
    user, question = await _posted(session, bot)
    assert await mentor_service.monthly_used(session, user) == 1
    later = question.created_at + timedelta(hours=48, minutes=5)

    first = await run_mentor_scan(bot, session, later)
    second = await run_mentor_scan(bot, session, later + timedelta(minutes=30))

    assert first.notified == 1 and second.notified == 0
    notices = bot.to_chat(user.telegram_id)
    assert len(notices) == 1 and f"#{question.public_number}" in notices[0].text
    assert await mentor_service.monthly_used(session, user) == 0
    # Savol ochiq qoladi — mentor hali javob berishi mumkin.
    assert (await _reload(session, question)).status == MentorQuestionStatus.OPEN


@pytest.mark.asyncio
async def test_answered_question_auto_closes_after_72_hours(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member"})
    user, question = await _posted(session, bot)
    question = await _claim(session, bot, question)
    answered_at = question.created_at + timedelta(hours=1)
    await mentor_service.accept_answer(
        session, question, mentor_tg_id=MENTOR, mentor_name="Ali", text=ANSWER_TEXT, now=answered_at
    )
    await session.commit()

    early = await run_mentor_scan(bot, session, answered_at + timedelta(hours=71))
    assert early.closed == 0

    result = await run_mentor_scan(bot, session, answered_at + timedelta(hours=72, minutes=1))
    fresh = await _reload(session, question)
    assert result.closed == 1
    assert fresh.status == MentorQuestionStatus.CLOSED
    prompt = bot.to_chat(user.telegram_id)[-1]
    assert prompt.reply_markup.inline_keyboard[0][0].callback_data == f"rate:{question.id}:1"


@pytest.mark.asyncio
async def test_answered_question_is_not_reminded_or_flagged(session, mentor_settings) -> None:
    """Javob olgan savol uchun 24/48 soatlik xabarlar ketmasligi kerak."""
    bot = FakeBot(members={MENTOR: "member"})
    user, question = await _posted(session, bot)
    question = await _claim(session, bot, question)
    await mentor_service.accept_answer(
        session,
        question,
        mentor_tg_id=MENTOR,
        mentor_name="Ali",
        text=ANSWER_TEXT,
        now=question.created_at + timedelta(hours=1),
    )
    await session.commit()

    result = await run_mentor_scan(bot, session, question.created_at + timedelta(hours=50))

    assert result.reminded == 0 and result.notified == 0
    assert await mentor_service.monthly_used(session, user) == 1
