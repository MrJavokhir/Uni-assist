"""Botdagi majburiy obuna: /start -> obuna -> xush kelibsiz.

/start til so'ramaydi (app/bot/handlers/start.py); chat tarixidagi eski til
tugmalari ham o'sha ekranga olib boradi (app/bot/handlers/language.py).
Diqqat markazida: obuna bo'lmagan odam Mini App tugmasini olmasligi,
ozod qilingan o'tishi va taklif mukofoti faqat obunadan keyin, BIR MARTA
berilishi.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.bot.handlers import language, start
from app.db.models import RequiredChannel, SubscriptionExemption, User
from app.services import payment_service

TG_ID = 4242


class _FakeMember:
    def __init__(self, status: str) -> None:
        self.status = status


class _FakeBot:
    status = "left"
    sent: list[int] = []

    async def get_chat_member(self, chat_id: str, user_id: int):
        return _FakeMember(_FakeBot.status)

    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        _FakeBot.sent.append(chat_id)


class _FakeMessage:
    def __init__(self) -> None:
        self.edits: list[tuple[str, object]] = []

    async def edit_text(self, text: str, reply_markup=None) -> None:
        self.edits.append((text, reply_markup))


class _FromUser:
    def __init__(self, telegram_id: int) -> None:
        self.id = telegram_id
        self.username = f"u{telegram_id}"
        self.full_name = "Aziz"


class _FakeCallback:
    def __init__(self, telegram_id: int = TG_ID, code: str = "uz") -> None:
        self.data = f"lang:{code}"
        self.from_user = _FromUser(telegram_id)
        self.bot = _FakeBot()
        self.message = _FakeMessage()

    async def answer(self, *args, **kwargs) -> None:
        pass


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    _FakeBot.status = "left"
    _FakeBot.sent = []
    # Kesh testlarni bir-biriga bog'lab qo'ymasin.
    monkeypatch.setattr(start, "redis_client", None)


async def _user(session, telegram_id: int = TG_ID, **kwargs) -> User:
    user = User(telegram_id=telegram_id, **kwargs)
    session.add(user)
    await session.flush()
    return user


async def _channel(session) -> None:
    session.add(
        RequiredChannel(title="Uni Assist", invite_url="https://t.me/uniassist_uz", is_active=True)
    )
    await session.flush()


def _buttons(markup) -> list:
    return [b for row in markup.inline_keyboard for b in row]


@pytest.mark.asyncio
async def test_no_channels_goes_straight_to_welcome(session) -> None:
    await _user(session)
    cb = _FakeCallback()

    await language.choose_language(cb, session)

    _, markup = cb.message.edits[-1]
    assert any(b.web_app for b in _buttons(markup)), "Mini App tugmasi bo'lishi kerak"


@pytest.mark.asyncio
async def test_not_member_sees_channels_after_language(session) -> None:
    await _channel(session)
    await _user(session)
    cb = _FakeCallback(code="ru")

    await language.choose_language(cb, session)

    text, markup = cb.message.edits[-1]
    buttons = _buttons(markup)
    assert [b.url for b in buttons if b.url] == ["https://t.me/uniassist_uz"]
    assert not any(b.web_app for b in buttons), "a'zo bo'lmaguncha Mini App berilmaydi"
    # So'rov tanlangan tilda chiqadi.
    assert any("а" <= ch <= "я" for ch in text)


@pytest.mark.asyncio
async def test_member_goes_to_welcome(session) -> None:
    await _channel(session)
    await _user(session)
    _FakeBot.status = "member"
    cb = _FakeCallback()

    await language.choose_language(cb, session)

    _, markup = cb.message.edits[-1]
    assert any(b.web_app for b in _buttons(markup))


@pytest.mark.asyncio
async def test_exempt_user_passes_without_joining(session) -> None:
    await _channel(session)
    await _user(session)
    session.add(SubscriptionExemption(telegram_id=TG_ID, is_active=True))
    await session.flush()
    cb = _FakeCallback()

    await language.choose_language(cb, session)

    _, markup = cb.message.edits[-1]
    assert any(b.web_app for b in _buttons(markup))


@pytest.mark.asyncio
async def test_referral_reward_only_after_subscription_and_once(session) -> None:
    settings_row = await payment_service.get_settings(session)
    settings_row.referral_bonus = Decimal(1000)
    await _channel(session)
    inviter = await _user(session, 5001)
    invited = await _user(session, referred_by_id=inviter.id)

    # Obunasiz — mukofot yo'q.
    await language.choose_language(_FakeCallback(), session)
    await session.refresh(inviter)
    assert Decimal(str(inviter.balance or 0)) == Decimal(0)

    # Obuna bo'ldi — mukofot va xabar.
    _FakeBot.status = "member"
    await language.choose_language(_FakeCallback(), session)
    await session.refresh(inviter)
    await session.refresh(invited)
    assert Decimal(str(inviter.balance)) == Decimal(1000)
    assert invited.referral_confirmed is True
    assert _FakeBot.sent == [5001]

    # Til qayta tanlansa (masalan /start takrorlanganda) pul takror berilmaydi.
    await language.choose_language(_FakeCallback(), session)
    await session.refresh(inviter)
    assert Decimal(str(inviter.balance)) == Decimal(1000)


class _FakeStartMessage:
    def __init__(self, telegram_id: int = TG_ID) -> None:
        self.from_user = _FromUser(telegram_id)
        self.from_user.language_code = "ru"
        self.bot = _FakeBot()
        self.answers: list[tuple[str, object]] = []

    async def answer(self, text: str, reply_markup=None) -> None:
        self.answers.append((text, reply_markup))


class _NoArgs:
    args = None


@pytest.mark.asyncio
async def test_start_skips_language_and_opens_in_english(session) -> None:
    """/start til so'ramaydi: yangi foydalanuvchi ingliz tilida, darhol xush kelibsiz.

    Telegram tili ruscha bo'lsa ham — til Mini App Profil'idan almashtiriladi.
    """
    msg = _FakeStartMessage()

    await start.cmd_start(msg, session, _NoArgs())

    text, markup = msg.answers[-1]
    assert "Tilni tanlang" not in text
    assert any(b.web_app for b in _buttons(markup)), "darhol Mini App tugmasi"
    user = (await session.execute(select(User).where(User.telegram_id == TG_ID))).scalar_one()
    assert user.ui_language.value == "en"


@pytest.mark.asyncio
async def test_start_asks_to_subscribe_in_english(session) -> None:
    await _channel(session)
    msg = _FakeStartMessage()

    await start.cmd_start(msg, session, _NoArgs())

    text, markup = msg.answers[-1]
    buttons = _buttons(markup)
    assert [b.url for b in buttons if b.url] == ["https://t.me/uniassist_uz"]
    assert not any(b.web_app for b in buttons)
    assert "join" in text.lower()
