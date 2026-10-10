"""Mentordan so'rash — Telegram tomoni (soxta bot bilan).

Handler'lar to'g'ridan-to'g'ri chaqiriladi; aiogram obyektlari o'rniga
kerakli maydonlari bor oddiy obyektlar beriladi.
"""

from types import SimpleNamespace

import pytest

from app.bot.handlers import mentor as handlers
from app.db.models import CountryTopic, MentorQuestionStatus, MentorSender
from app.services import mentor_group, mentor_service
from tests.mentor_fakes import (
    ANSWER_TEXT,
    GROUP_ID,
    FakeBot,
    add_country,
    add_user,
    make_question,
)

MENTOR = 7001
OTHER_MENTOR = 7002
OUTSIDER = 7003


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def __call__(self, text=None, **kwargs):
        self.calls.append((text, kwargs))

    @property
    def texts(self) -> list[str]:
        return [c[0] for c in self.calls]


def _callback(data: str, tg_id: int, name: str = "Ali Valiyev", username: str | None = None):
    return SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=tg_id, full_name=name, username=username),
        answer=Recorder(),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=GROUP_ID), edit_reply_markup=Recorder(), edit_text=Recorder()
        ),
    )


def _group_message(text, *, sender: int, reply_to: int | None, message_id: int = 5000):
    return SimpleNamespace(
        text=text,
        from_user=SimpleNamespace(id=sender, full_name="Ali Valiyev", username="ali"),
        reply_to_message=SimpleNamespace(message_id=reply_to) if reply_to else None,
        chat=SimpleNamespace(id=GROUP_ID),
        message_id=message_id,
        reply=Recorder(),
    )


async def _posted(session, bot, telegram_id: int = 500):
    user = await add_user(session, telegram_id)
    if await mentor_group.get_country(session, "DE") is None:
        await add_country(session)
    question = await make_question(session, user)
    await mentor_group.post_question(bot, session, question)
    return user, question


async def _claim(session, bot, question, tg_id=MENTOR):
    callback = _callback(f"claim:{question.id}", tg_id, username="ali")
    await handlers.on_claim(callback, session, bot)
    return callback


# ---------------------------------------------------------------- joylash va topic


@pytest.mark.asyncio
async def test_question_posted_to_country_topic_without_user_data(session, mentor_settings) -> None:
    bot = FakeBot()
    user, question = await _posted(session, bot, telegram_id=123456789)

    assert bot.topics_created == ["🇩🇪 Germaniya"]
    posted = bot.to_chat(GROUP_ID)[-1]
    assert posted.thread_id is not None
    assert bot.has_claim_button(posted.reply_markup)
    assert f"#{question.public_number}" in posted.text
    # Foydalanuvchi haqida hech narsa yo'q.
    assert "123456789" not in posted.text
    assert user.username not in posted.text
    assert question.group_message_id == posted.message_id

    # Ikkinchi savol o'sha topic'ga tushadi, yangisi ochilmaydi.
    await _posted(session, bot, telegram_id=600)
    assert bot.topics_created == ["🇩🇪 Germaniya"]
    assert bot.to_chat(GROUP_ID)[-1].thread_id == posted.thread_id


@pytest.mark.asyncio
async def test_deleted_topic_is_recreated_and_message_resent(session, mentor_settings) -> None:
    bot = FakeBot()
    await _posted(session, bot)
    old_thread = bot.to_chat(GROUP_ID)[-1].thread_id

    bot.deleted_threads.add(old_thread)  # admin topic'ni o'chirib yubordi
    _, second = await _posted(session, bot, telegram_id=601)

    assert len(bot.topics_created) == 2
    new_post = bot.to_chat(GROUP_ID)[-1]
    assert new_post.thread_id != old_thread
    assert second.group_message_id == new_post.message_id
    row = await session.get(CountryTopic, "DE", populate_existing=True)
    assert row.message_thread_id == new_post.thread_id


# ---------------------------------------------------------------- claim


@pytest.mark.asyncio
async def test_non_member_cannot_claim(session, mentor_settings) -> None:
    bot = FakeBot(members={OUTSIDER: "left"})
    _, question = await _posted(session, bot)

    callback = await _claim(session, bot, question, tg_id=OUTSIDER)

    assert callback.answer.calls[-1] == ("Faqat mentorlar javob bera oladi.", {"show_alert": True})
    fresh = await mentor_service.get_question(session, question.id)
    assert fresh.status == MentorQuestionStatus.OPEN


@pytest.mark.asyncio
async def test_member_claims_and_gets_force_reply(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member", OTHER_MENTOR: "administrator"}, usernames={MENTOR: "ali"})
    _, question = await _posted(session, bot)

    await _claim(session, bot, question)
    fresh = await mentor_service.get_question(session, question.id)

    assert fresh.status == MentorQuestionStatus.CLAIMED
    assert fresh.claimed_by_tg_id == MENTOR
    # Asl xabar: tugma olib tashlandi, kim javob berayotgani yozildi.
    edit = bot.edits[-1]
    assert edit["message_id"] == question.group_message_id
    assert edit["reply_markup"] is None
    assert "Ali Valiyev javob bermoqda" in edit["text"]
    # ForceReply asl xabarga reply bo'lib, mentorni tilga oladi.
    force = bot.to_chat(GROUP_ID)[-1]
    assert force.reply_to == question.group_message_id
    assert "@ali" in force.text
    assert getattr(force.reply_markup, "force_reply", False) is True
    assert force.reply_markup.selective is True
    assert fresh.force_reply_message_id == force.message_id

    # Ikkinchi mentor kech qoldi.
    late = await _claim(session, bot, question, tg_id=OTHER_MENTOR)
    assert late.answer.calls[-1] == ("Bu savolni boshqa mentor oldi.", {"show_alert": True})


# ---------------------------------------------------------------- javob


async def _claimed(session, bot):
    user, question = await _posted(session, bot)
    await _claim(session, bot, question)
    return user, await mentor_service.get_question(session, question.id)


@pytest.mark.asyncio
async def test_answer_delivered_anonymously(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member"})
    user, question = await _claimed(session, bot)

    message = _group_message(ANSWER_TEXT, sender=MENTOR, reply_to=question.force_reply_message_id)
    await handlers.on_group_message(message, session, bot)

    to_user = bot.to_chat(user.telegram_id)
    assert len(to_user) == 1
    assert ANSWER_TEXT.split(".")[0] in to_user[0].text
    # Mentorning ismi va username'i foydalanuvchiga ko'rinmaydi.
    assert "Ali" not in to_user[0].text and "@ali" not in to_user[0].text
    fresh = await mentor_service.get_question(session, question.id)
    assert fresh.status == MentorQuestionStatus.ANSWERED
    assert "✅ Javob berildi" in bot.edits[-1]["text"]
    assert bot.reactions == [message.message_id]


@pytest.mark.asyncio
async def test_wrong_sender_and_wrong_reply_are_ignored(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member", OTHER_MENTOR: "member"})
    user, question = await _claimed(session, bot)

    stranger = _group_message(ANSWER_TEXT, sender=OTHER_MENTOR, reply_to=question.force_reply_message_id)
    await handlers.on_group_message(stranger, session, bot)
    chatter = _group_message(ANSWER_TEXT, sender=MENTOR, reply_to=question.group_message_id)
    await handlers.on_group_message(chatter, session, bot)
    plain = _group_message(ANSWER_TEXT, sender=MENTOR, reply_to=None)
    await handlers.on_group_message(plain, session, bot)

    assert bot.to_chat(user.telegram_id) == []
    assert stranger.reply.calls == chatter.reply.calls == plain.reply.calls == []
    fresh = await mentor_service.get_question(session, question.id)
    assert fresh.status == MentorQuestionStatus.CLAIMED


@pytest.mark.asyncio
async def test_media_and_contacts_get_a_reply_and_force_reply_stays(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member"})
    user, question = await _claimed(session, bot)
    force_id = question.force_reply_message_id

    photo = _group_message(None, sender=MENTOR, reply_to=force_id)
    await handlers.on_group_message(photo, session, bot)
    contact = _group_message(ANSWER_TEXT + " Yozing: @ali_mentor", sender=MENTOR, reply_to=force_id)
    await handlers.on_group_message(contact, session, bot)

    assert photo.reply.texts == ["Faqat matnli javob qabul qilinadi."]
    assert "kontakt yoki begona havola" in contact.reply.texts[0]
    assert bot.to_chat(user.telegram_id) == []
    fresh = await mentor_service.get_question(session, question.id)
    assert fresh.force_reply_message_id == force_id  # qayta yozsa bo'ladi

    good = _group_message(ANSWER_TEXT, sender=MENTOR, reply_to=force_id)
    await handlers.on_group_message(good, session, bot)
    assert len(bot.to_chat(user.telegram_id)) == 1


# ---------------------------------------------------------------- mentor chiqib ketdi


@pytest.mark.asyncio
async def test_leaving_mentor_releases_claimed_questions(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member"})
    _, question = await _claimed(session, bot)
    force_id = question.force_reply_message_id

    event = SimpleNamespace(
        new_chat_member=SimpleNamespace(status="left", user=SimpleNamespace(id=MENTOR)),
        chat=SimpleNamespace(id=GROUP_ID),
    )
    await handlers.on_member_update(event, session, bot)

    fresh = await mentor_service.get_question(session, question.id)
    assert fresh.status == MentorQuestionStatus.OPEN
    assert fresh.claimed_by_tg_id is None
    assert force_id in bot.deleted
    assert bot.has_claim_button(bot.edits[-1]["reply_markup"])


@pytest.mark.asyncio
async def test_followup_goes_to_same_mentor_with_force_reply(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member"}, usernames={MENTOR: "ali"})
    user, question = await _claimed(session, bot)
    await handlers.on_group_message(
        _group_message(ANSWER_TEXT, sender=MENTOR, reply_to=question.force_reply_message_id),
        session,
        bot,
    )
    question = await mentor_service.get_question(session, question.id)

    await mentor_group.submit_followup(bot, session, question, user, "Viza qancha vaqt oladi?")

    posts = bot.to_chat(GROUP_ID)
    followup, force = posts[-2], posts[-1]
    assert followup.text.startswith(f"↪️ Savol #{question.public_number}")
    assert followup.reply_to == question.group_message_id
    assert force.reply_to == followup.message_id and "@ali" in force.text
    assert question.status == MentorQuestionStatus.CLAIMED
    assert question.force_reply_message_id == force.message_id


@pytest.mark.asyncio
async def test_followup_reopens_when_mentor_left(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member"})
    user, question = await _claimed(session, bot)
    await handlers.on_group_message(
        _group_message(ANSWER_TEXT, sender=MENTOR, reply_to=question.force_reply_message_id),
        session,
        bot,
    )
    question = await mentor_service.get_question(session, question.id)
    bot.members[MENTOR] = "left"

    await mentor_group.submit_followup(bot, session, question, user, "Viza qancha vaqt oladi?")

    post = bot.to_chat(GROUP_ID)[-1]
    assert bot.has_claim_button(post.reply_markup)
    assert question.status == MentorQuestionStatus.OPEN
    assert question.claimed_by_tg_id is None
    assert question.group_message_id == post.message_id
    loaded = await mentor_service.get_question(session, question.id)
    assert [m.sender for m in loaded.messages][-1] == MentorSender.USER


# ---------------------------------------------------------------- yopish va baho


@pytest.mark.asyncio
async def test_close_button_asks_for_rating_and_rating_updates_group(session, mentor_settings) -> None:
    bot = FakeBot(members={MENTOR: "member"})
    user, question = await _claimed(session, bot)
    await handlers.on_group_message(
        _group_message(ANSWER_TEXT, sender=MENTOR, reply_to=question.force_reply_message_id),
        session,
        bot,
    )

    close_cb = _callback(f"close:{question.id}", user.telegram_id)
    await handlers.on_close(close_cb, session, bot)
    prompt = bot.to_chat(user.telegram_id)[-1]
    assert [b.callback_data for b in prompt.reply_markup.inline_keyboard[0]] == [
        f"rate:{question.id}:{n}" for n in range(1, 6)
    ]

    rate_cb = _callback(f"rate:{question.id}:5", user.telegram_id)
    await handlers.on_rate(rate_cb, session, bot)
    fresh = await mentor_service.get_question(session, question.id)
    assert fresh.status == MentorQuestionStatus.CLOSED and fresh.rating == 5
    assert "🔒 Yopildi · ⭐ 5" in bot.edits[-1]["text"]
