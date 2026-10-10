"""Mentordan so'rash — bazadagi qoidalar (Telegram'siz).

Diqqat markazida: ikki mentor bir savolni ololmasligi, javob faqat to'g'ri
mentordan va to'g'ri ForceReply'ga reply bo'lsa qabul qilinishi, limitlar.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import MentorQuestion, MentorQuestionStatus, MentorSender
from app.services import mentor_service
from app.services.mentor_service import AnswerVerdict, MentorError
from tests.conftest import TEST_DATABASE_URL
from tests.mentor_fakes import (
    ANSWER_TEXT,
    add_country,
    add_user,
    make_question,
)

MENTOR_A = 7001
MENTOR_B = 7002


async def _claimed(session, mentor=MENTOR_A, force_reply=555):
    user = await add_user(session)
    await add_country(session)
    question = await make_question(session, user)
    question = await mentor_service.claim(
        session, question.id, mentor_tg_id=mentor, mentor_name="Ali"
    )
    question.force_reply_message_id = force_reply
    await session.flush()
    return user, question


# ---------------------------------------------------------------- savol berish


@pytest.mark.asyncio
async def test_question_gets_public_number_and_first_message(session, mentor_settings) -> None:
    user = await add_user(session)
    await add_country(session)

    question = await make_question(session, user)
    loaded = await mentor_service.get_question(session, question.id)

    assert loaded.public_number >= 100
    assert loaded.status == MentorQuestionStatus.OPEN
    assert [m.sender for m in loaded.messages] == [MentorSender.USER]


@pytest.mark.asyncio
async def test_inactive_country_and_length_are_rejected(session, mentor_settings) -> None:
    user = await add_user(session)
    with pytest.raises(MentorError, match="country_inactive"):
        await make_question(session, user, country_code="US")
    with pytest.raises(MentorError, match="text_too_short"):
        await make_question(session, user, text="Juda qisqa savol")
    with pytest.raises(MentorError, match="text_too_long"):
        await make_question(session, user, text="x" * 1001)


@pytest.mark.asyncio
async def test_monthly_limit(session, mentor_settings) -> None:
    user = await add_user(session)
    for _ in range(3):
        await make_question(session, user)

    with pytest.raises(MentorError, match="monthly_limit"):
        await make_question(session, user)


@pytest.mark.asyncio
async def test_unanswered_48h_question_is_not_counted(session, mentor_settings) -> None:
    """Mentorlar band bo'lgani uchun foydalanuvchi limitini yo'qotmaydi."""
    user = await add_user(session)
    questions = [await make_question(session, user) for _ in range(3)]
    questions[0].user_notified_48h = True
    await session.flush()

    assert await mentor_service.monthly_used(session, user) == 2
    await make_question(session, user)  # limit yana bo'shadi


@pytest.mark.asyncio
async def test_previous_month_is_not_counted(session, mentor_settings) -> None:
    user = await add_user(session)
    last_month = datetime.now(UTC) - timedelta(days=40)
    for _ in range(3):
        await make_question(session, user, now=last_month)

    assert await mentor_service.monthly_used(session, user) == 0


# ---------------------------------------------------------------- biriktirish


@pytest.mark.asyncio
async def test_second_claim_fails(session, mentor_settings) -> None:
    user = await add_user(session)
    question = await make_question(session, user)

    first = await mentor_service.claim(session, question.id, mentor_tg_id=MENTOR_A, mentor_name="A")
    second = await mentor_service.claim(session, question.id, mentor_tg_id=MENTOR_B, mentor_name="B")

    assert first is not None and first.claimed_by_tg_id == MENTOR_A
    assert second is None


@pytest.mark.asyncio
async def test_concurrent_claims_only_one_wins(session, mentor_settings) -> None:
    """Ikki mentor AYNAN bir vaqtda bosadi — ikki alohida ulanish."""
    user = await add_user(session)
    question = await make_question(session, user)
    await session.commit()

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    start = asyncio.Event()

    async def attempt(mentor_id: int):
        async with factory() as own:
            await start.wait()
            result = await mentor_service.claim(
                own, question.id, mentor_tg_id=mentor_id, mentor_name=str(mentor_id)
            )
            # Telegram chaqiruvlari davomida qulf ushlab turiladi.
            await asyncio.sleep(0.05)
            await own.commit()
            return result

    try:
        tasks = [asyncio.create_task(attempt(m)) for m in (MENTOR_A, MENTOR_B)]
        await asyncio.sleep(0.05)
        start.set()
        results = await asyncio.gather(*tasks)
    finally:
        await engine.dispose()

    winners = [r for r in results if r is not None]
    assert len(winners) == 1
    session.expunge_all()
    saved = (
        await session.execute(select(MentorQuestion).where(MentorQuestion.id == question.id))
    ).scalar_one()
    assert saved.claimed_by_tg_id == winners[0].claimed_by_tg_id


# ---------------------------------------------------------------- javob


@pytest.mark.asyncio
async def test_answer_accepted_only_from_claimer_on_current_force_reply(
    session, mentor_settings
) -> None:
    _, question = await _claimed(session, force_reply=555)

    def verdict(**kw):
        params = {"sender_tg_id": MENTOR_A, "reply_to_message_id": 555, "text": ANSWER_TEXT}
        params.update(kw)
        return mentor_service.check_answer(question, **params)

    assert verdict() == AnswerVerdict.OK
    # Boshqa mentor o'sha xabarga reply qildi — e'tiborsiz.
    assert verdict(sender_tg_id=MENTOR_B) == AnswerVerdict.IGNORE
    # Boshqa xabarga reply — e'tiborsiz (mentorlar suhbati).
    assert verdict(reply_to_message_id=777) == AnswerVerdict.IGNORE
    assert verdict(reply_to_message_id=None) == AnswerVerdict.IGNORE
    assert mentor_service.check_answer(
        None, sender_tg_id=MENTOR_A, reply_to_message_id=555, text=ANSWER_TEXT
    ) == AnswerVerdict.IGNORE


@pytest.mark.asyncio
async def test_non_text_short_and_contact_answers_are_rejected(session, mentor_settings) -> None:
    _, question = await _claimed(session, force_reply=555)
    base = {"sender_tg_id": MENTOR_A, "reply_to_message_id": 555}

    # Rasm, fayl, ovoz, stiker — `text` yo'q.
    assert mentor_service.check_answer(question, text=None, **base) == AnswerVerdict.NOT_TEXT
    assert mentor_service.check_answer(question, text="Ha, mumkin.", **base) == AnswerVerdict.TOO_SHORT
    contact = ANSWER_TEXT + " Batafsil: @mentor_ali"
    assert mentor_service.check_answer(question, text=contact, **base) == AnswerVerdict.CONTACT


@pytest.mark.asyncio
async def test_accept_answer_once(session, mentor_settings) -> None:
    _, question = await _claimed(session)

    first = await mentor_service.accept_answer(
        session, question, mentor_tg_id=MENTOR_A, mentor_name="Ali", text=ANSWER_TEXT
    )
    second = await mentor_service.accept_answer(
        session, question, mentor_tg_id=MENTOR_A, mentor_name="Ali", text=ANSWER_TEXT
    )

    assert first is not None and second is None
    assert question.status == MentorQuestionStatus.ANSWERED
    assert question.answered_at is not None
    # Eski ForceReply'ga yozilgan keyingi xabar javob bo'lmaydi.
    assert question.force_reply_message_id is None


# ---------------------------------------------------------------- qo'shimcha savol


async def _answered(session):
    user, question = await _claimed(session)
    await mentor_service.accept_answer(
        session, question, mentor_tg_id=MENTOR_A, mentor_name="Ali", text=ANSWER_TEXT
    )
    return user, question


@pytest.mark.asyncio
async def test_followup_only_after_answer_and_within_limit(session, mentor_settings) -> None:
    user, question = await _claimed(session)
    with pytest.raises(MentorError, match="followup_not_allowed"):
        await mentor_service.add_followup(session, question, user, "Yana bir savol bor edi")

    await mentor_service.accept_answer(
        session, question, mentor_tg_id=MENTOR_A, mentor_name="Ali", text=ANSWER_TEXT
    )
    for i in range(3):
        await mentor_service.add_followup(session, question, user, f"Aniqlashtirish {i}")
        assert question.status == MentorQuestionStatus.CLAIMED
        assert question.claimed_by_tg_id == MENTOR_A  # o'sha mentorga qaytadi
        question.force_reply_message_id = 900 + i
        await mentor_service.accept_answer(
            session, question, mentor_tg_id=MENTOR_A, mentor_name="Ali", text=ANSWER_TEXT
        )

    assert await mentor_service.followups_used(session, question) == 3
    with pytest.raises(MentorError, match="followup_limit"):
        await mentor_service.add_followup(session, question, user, "To'rtinchisi")


@pytest.mark.asyncio
async def test_followup_by_other_user_is_rejected(session, mentor_settings) -> None:
    _, question = await _answered(session)
    stranger = await add_user(session, telegram_id=501)
    with pytest.raises(MentorError, match="not_found"):
        await mentor_service.add_followup(session, question, stranger, "Begona savol")


# ---------------------------------------------------------------- yopish va baho


@pytest.mark.asyncio
async def test_close_and_rate_once(session, mentor_settings) -> None:
    user, question = await _answered(session)

    with pytest.raises(MentorError):
        await mentor_service.rate(session, question, user, 6)
    assert await mentor_service.rate(session, question, user, 5) is False  # hali yopilmagan

    assert await mentor_service.close(session, question) is True
    assert await mentor_service.close(session, question) is False
    assert await mentor_service.rate(session, question, user, 4) is True
    assert await mentor_service.rate(session, question, user, 1) is False
    assert question.rating == 4


@pytest.mark.asyncio
async def test_complaint_only_on_own_question_mentor_message(session, mentor_settings) -> None:
    from app.db.models import ComplaintReason

    user, question = await _answered(session)
    loaded = await mentor_service.get_question(session, question.id)
    user_msg = next(m for m in loaded.messages if m.sender == MentorSender.USER)
    mentor_msg = next(m for m in loaded.messages if m.sender == MentorSender.MENTOR)

    complaint = await mentor_service.add_complaint(
        session, loaded, user, reason=ComplaintReason.PAID_OR_AD, message_id=mentor_msg.id
    )
    assert complaint.message_id == mentor_msg.id

    with pytest.raises(MentorError, match="bad_message"):
        await mentor_service.add_complaint(
            session, loaded, user, reason=ComplaintReason.OTHER, message_id=user_msg.id
        )
    stranger = await add_user(session, telegram_id=502)
    with pytest.raises(MentorError, match="not_found"):
        await mentor_service.add_complaint(
            session, loaded, stranger, reason=ComplaintReason.OTHER
        )
