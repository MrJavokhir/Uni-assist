"""Mini App API — "Mentordan so'rash".

Endpoint funksiyalari to'g'ridan-to'g'ri chaqiriladi, Telegram o'rniga
soxta bot. Asosiy tekshiruv: foydalanuvchiga mentorning ismi yoki ID'si
HECH QACHON qaytmasligi.
"""

from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException

from app.services import mentor_group, mentor_service
from app.webapp import mentor_api
from app.webapp.schemas import (
    MentorComplaintIn,
    MentorQuestionIn,
    MentorRatingIn,
    MentorTextIn,
)
from tests.mentor_fakes import (
    ANSWER_TEXT,
    GROUP_ID,
    QUESTION_TEXT,
    FakeBot,
    add_country,
    add_user,
)

MENTOR = 7001


@pytest.fixture
def bot(monkeypatch, mentor_settings):
    fake = FakeBot(members={MENTOR: "member"})

    @asynccontextmanager
    async def _fake():
        yield fake

    monkeypatch.setattr(mentor_api, "_bot", _fake)
    return fake


def _payload(**kw) -> MentorQuestionIn:
    data = {"country_code": "DE", "level": "master", "topic": "visa", "text": QUESTION_TEXT}
    data.update(kw)
    return MentorQuestionIn(**data)


async def _answer(session, bot, question_id: int) -> None:
    question = await mentor_service.claim(
        session, question_id, mentor_tg_id=MENTOR, mentor_name="Ali Valiyev"
    )
    await mentor_group.deliver_answer(
        bot, session, question, mentor_tg_id=MENTOR, mentor_name="Ali Valiyev", text_body=ANSWER_TEXT
    )
    await session.commit()


@pytest.mark.asyncio
async def test_config_lists_active_countries_and_quota(session, bot) -> None:
    user = await add_user(session)
    await add_country(session, "DE", "Germaniya")
    await add_country(session, "KR", "Koreya")
    await add_country(session, "US", "AQSh")

    config = await mentor_api.mentor_config(user=user, session=session)

    assert config.enabled is True
    assert [c.code for c in config.countries] == ["DE", "KR"]  # sozlamadagi tartib
    assert config.countries[0].flag == "🇩🇪"
    assert (config.monthly_used, config.monthly_limit) == (0, 3)


@pytest.mark.asyncio
async def test_ask_posts_to_group_and_returns_chat(session, bot) -> None:
    user = await add_user(session)
    await add_country(session)

    result = await mentor_api.ask_question(_payload(), user=user, session=session)

    assert result.status == "open"
    assert [m.sender for m in result.messages] == ["user"]
    assert len(bot.to_chat(GROUP_ID)) == 1


@pytest.mark.asyncio
async def test_limit_returns_code(session, bot) -> None:
    user = await add_user(session)
    await add_country(session)
    for _ in range(3):
        await mentor_api.ask_question(_payload(), user=user, session=session)

    with pytest.raises(HTTPException) as exc:
        await mentor_api.ask_question(_payload(), user=user, session=session)
    assert exc.value.detail == {"code": "monthly_limit"}


@pytest.mark.asyncio
async def test_failed_post_does_not_use_up_the_limit(session, bot, monkeypatch) -> None:
    """Guruhga tushmagan savol "yuborildi" deb ko'rinmasligi va limitni yemasligi kerak."""
    user = await add_user(session)
    await add_country(session)
    # Commit: rollback foydalanuvchining o'zini o'chirib yubormasin — aks
    # holda bo'sh ro'yxat hech narsani isbotlamasdi.
    await session.commit()

    async def broken(*args, **kwargs):
        raise RuntimeError("telegram down")

    monkeypatch.setattr(mentor_group, "post_question", broken)
    with pytest.raises(HTTPException) as exc:
        await mentor_api.ask_question(_payload(), user=user, session=session)

    assert exc.value.detail == {"code": "send_failed"}
    await session.refresh(user)  # rollback obyektlarni eskirtiradi
    assert await mentor_api.my_questions(user=user, session=session) == []
    assert await mentor_service.monthly_used(session, user) == 0



@pytest.mark.asyncio
async def test_mentor_identity_never_reaches_the_user(session, bot) -> None:
    user = await add_user(session)
    await add_country(session)
    asked = await mentor_api.ask_question(_payload(), user=user, session=session)
    await _answer(session, bot, asked.id)

    result = await mentor_api.get_question(asked.id, user=user, session=session)
    dumped = result.model_dump_json()

    assert result.status == "answered"
    assert [m.sender for m in result.messages] == ["user", "mentor"]
    assert "Ali" not in dumped and str(MENTOR) not in dumped
    assert result.can_followup and result.can_close and result.can_complain


@pytest.mark.asyncio
async def test_other_users_question_is_not_found(session, bot) -> None:
    owner = await add_user(session)
    stranger = await add_user(session, telegram_id=501)
    await add_country(session)
    asked = await mentor_api.ask_question(_payload(), user=owner, session=session)

    with pytest.raises(HTTPException) as exc:
        await mentor_api.get_question(asked.id, user=stranger, session=session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_followup_close_rate_flow(session, bot) -> None:
    user = await add_user(session)
    await add_country(session)
    asked = await mentor_api.ask_question(_payload(), user=user, session=session)
    await _answer(session, bot, asked.id)

    after_followup = await mentor_api.follow_up(
        asked.id, MentorTextIn(text="Yana bir narsa so'ramoqchi edim"), user=user, session=session
    )
    assert after_followup.status == "claimed"
    assert after_followup.followups_left == 2
    assert after_followup.can_followup is False  # javob kutilmoqda

    # Mentor qo'shimcha savolga javob beradi.
    question = await mentor_service.get_question(session, asked.id)
    await mentor_group.deliver_answer(
        bot, session, question, mentor_tg_id=MENTOR, mentor_name="Ali", text_body=ANSWER_TEXT
    )
    await session.commit()

    closed = await mentor_api.close_question(asked.id, user=user, session=session)
    assert closed.status == "closed" and closed.can_rate

    rated = await mentor_api.rate_question(asked.id, MentorRatingIn(rating=4), user=user, session=session)
    assert rated.rating == 4 and rated.can_rate is False


@pytest.mark.asyncio
async def test_complaint_notifies_admin(session, bot) -> None:
    user = await add_user(session)
    await add_country(session)
    asked = await mentor_api.ask_question(_payload(), user=user, session=session)
    await _answer(session, bot, asked.id)
    detail = await mentor_api.get_question(asked.id, user=user, session=session)
    mentor_msg = detail.messages[-1]

    await mentor_api.complain(
        asked.id,
        MentorComplaintIn(reason="paid_or_ad", comment="Pullik konsultatsiya taklif qildi", message_id=mentor_msg.id),
        user=user,
        session=session,
    )

    alert = bot.to_chat(999)[-1].text
    assert f"#{asked.number}" in alert and "Pullik xizmat yoki reklama" in alert
