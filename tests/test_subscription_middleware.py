"""SubscriptionMiddleware'ning haqiqiy aiogram Update obyektlari bilan xatti-harakati."""

from datetime import UTC, datetime

import pytest
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TgUser

from app.bot.keyboards import SUBSCRIPTION_CHECK_CALLBACK
from app.bot.middlewares import SubscriptionMiddleware
from app.db.models import RequiredChannel
from app.services.redis_client import redis_client
from app.services.subscription_service import clear_cache

TG_ID = 777


class _FakeMember:
    def __init__(self, status: str) -> None:
        self.status = status


class _FakeBot:
    def __init__(self, status: str) -> None:
        self.status = status

    async def get_chat_member(self, chat_id: str, user_id: int):
        return _FakeMember(self.status)


def _tg_user() -> TgUser:
    return TgUser(id=TG_ID, is_bot=False, first_name="Sanjar", username="sanjar")


def _message_update(sent: list, text: str = "Salom") -> tuple[Update, Message]:
    message = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=TG_ID, type="private"),
        from_user=_tg_user(),
        text=text,
    )
    # aiogram modellari frozen — javob yuborishni monkeypatch qilib kuzatamiz.
    async def answer(text, **kwargs):
        sent.append(text)

    object.__setattr__(message, "answer", answer)
    return Update(update_id=1, message=message), message


def _callback_update(data: str, answered: list) -> Update:
    message = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=TG_ID, type="private"),
        from_user=_tg_user(),
    )
    callback = CallbackQuery(
        id="1", from_user=_tg_user(), chat_instance="x", data=data, message=message
    )

    async def answer(text=None, **kwargs):
        answered.append(text)

    async def msg_answer(text, **kwargs):
        answered.append(text)

    object.__setattr__(callback, "answer", answer)
    object.__setattr__(message, "answer", msg_answer)
    return Update(update_id=1, callback_query=callback)


async def _run(session, update, bot):
    # Testlar bir xil telegram_id dan foydalanadi — oldingi testning Redis
    # keshi natijaga ta'sir qilmasligi uchun uni tozalaymiz.
    await clear_cache(redis_client, TG_ID)
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "handled"

    result = await SubscriptionMiddleware()(
        handler,
        update,
        {"event_from_user": update.event.from_user, "session": session, "bot": bot},
    )
    return result, calls


@pytest.mark.asyncio
async def test_passes_through_when_no_channels_configured(session) -> None:
    update, _ = _message_update([])
    result, calls = await _run(session, update, _FakeBot("left"))
    assert result == "handled"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_blocks_unsubscribed_user(session) -> None:
    session.add(RequiredChannel(title="Uni Assist", invite_url="https://t.me/uniassist_uz"))
    await session.commit()

    sent: list[str] = []
    # Ataylab /start EMAS: /start til tanlash uchun ozod qilingan.
    update, _ = _message_update(sent, text="Salom")
    result, calls = await _run(session, update, _FakeBot("left"))

    assert result is None
    assert calls == []
    assert len(sent) == 1
    # Kanal nomi endi xabar matnida emas, tugmada turadi.
    assert sent[0]


@pytest.mark.asyncio
async def test_start_is_never_blocked(session) -> None:
    """Birinchi qadam — til tanlash, shuning uchun /start hech qachon
    to'silmaydi. Aks holda yangi foydalanuvchi til tanlash oynasini umuman
    ko'rmay, obuna so'rovini standart tilda olardi."""
    session.add(RequiredChannel(title="Uni Assist", invite_url="https://t.me/uniassist_uz"))
    await session.commit()

    sent: list[str] = []
    update, _ = _message_update(sent, text="/start")
    result, calls = await _run(session, update, _FakeBot("left"))

    assert result == "handled"
    assert len(calls) == 1
    assert sent == []


@pytest.mark.asyncio
async def test_start_with_deeplink_is_never_blocked(session) -> None:
    session.add(RequiredChannel(title="Uni Assist", invite_url="https://t.me/uniassist_uz"))
    await session.commit()

    update, _ = _message_update([], text="/start ref123")
    result, calls = await _run(session, update, _FakeBot("left"))

    assert result == "handled"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_allows_subscribed_user(session) -> None:
    session.add(RequiredChannel(title="Uni Assist", invite_url="https://t.me/uniassist_uz"))
    await session.commit()

    update, _ = _message_update([])
    result, calls = await _run(session, update, _FakeBot("member"))

    assert result == "handled"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_check_button_is_never_blocked(session) -> None:
    """Aks holda obuna bo'lgan foydalanuvchi holatini yangilay olmay qolardi."""
    session.add(RequiredChannel(title="Uni Assist", invite_url="https://t.me/uniassist_uz"))
    await session.commit()

    answered: list[str] = []
    update = _callback_update(SUBSCRIPTION_CHECK_CALLBACK, answered)
    result, calls = await _run(session, update, _FakeBot("left"))

    assert result == "handled"
    assert len(calls) == 1
    assert answered == []


@pytest.mark.asyncio
async def test_other_callbacks_are_blocked(session) -> None:
    session.add(RequiredChannel(title="Uni Assist", invite_url="https://t.me/uniassist_uz"))
    await session.commit()

    answered: list[str] = []
    update = _callback_update("reminder:done:1", answered)
    result, calls = await _run(session, update, _FakeBot("left"))

    assert result is None
    assert calls == []
    assert len(answered) == 2  # alert + kanal ro'yxati xabari


@pytest.mark.asyncio
async def test_language_callback_is_never_blocked(session) -> None:
    """Til tanlash obuna to'sig'idan oldin bo'lishi kerak.

    Aks holda foydalanuvchi hali tilni tanlamasdan turib, o'zi tushunmaydigan
    tilda kanal so'rovini ko'rardi.
    """
    session.add(RequiredChannel(title="Uni Assist", invite_url="https://t.me/uniassist_uz"))
    await session.commit()

    answered: list[str] = []
    update = _callback_update("lang:ru", answered)
    result, calls = await _run(session, update, _FakeBot("left"))

    assert result == "handled"
    assert len(calls) == 1
    assert answered == []
