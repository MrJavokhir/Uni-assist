"""Mini App'dagi majburiy obuna tekshiruvi (`/subscription`).

Obuna botning /start'idan shu yerga ko'chgan, taklif mukofoti ham u bilan
birga. Shuning uchun diqqat markazida: obuna bo'lmagan odam to'xtatilishi,
ozod qilingan o'tishi va mukofot faqat obunadan keyin, BIR MARTA berilishi.
"""

from decimal import Decimal

import pytest

from app.db.models import RequiredChannel, SubscriptionExemption, User
from app.services import payment_service
from app.webapp import api

TG_ID = 4242


class _FakeMember:
    def __init__(self, status: str) -> None:
        self.status = status


class _FakeSession:
    async def close(self) -> None:
        pass


class _FakeBot:
    """`api.Bot` o'rniga. Holat sinf darajasida — endpoint nusxani o'zi yaratadi."""

    status = "left"
    sent: list[int] = []

    def __init__(self, *args, **kwargs) -> None:
        self.session = _FakeSession()

    async def get_chat_member(self, chat_id: str, user_id: int):
        return _FakeMember(_FakeBot.status)

    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        _FakeBot.sent.append(chat_id)


@pytest.fixture(autouse=True)
def _fake_bot(monkeypatch):
    _FakeBot.status = "left"
    _FakeBot.sent = []
    monkeypatch.setattr(api, "Bot", _FakeBot)
    monkeypatch.setattr(api.settings, "bot_token", "123:test")
    # Kesh testlarni bir-biriga bog'lab qo'ymasin.
    monkeypatch.setattr(api, "redis_client", None)


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


@pytest.mark.asyncio
async def test_no_channels_means_subscribed(session) -> None:
    user = await _user(session)

    result = await api.get_subscription(fresh=False, user=user, session=session)

    assert result.subscribed is True
    assert result.channels == []


@pytest.mark.asyncio
async def test_not_member_gets_channel_list(session) -> None:
    await _channel(session)
    user = await _user(session)

    result = await api.get_subscription(fresh=False, user=user, session=session)

    assert result.subscribed is False
    assert [c.invite_url for c in result.channels] == ["https://t.me/uniassist_uz"]


@pytest.mark.asyncio
async def test_member_passes(session) -> None:
    await _channel(session)
    user = await _user(session)
    _FakeBot.status = "member"

    result = await api.get_subscription(fresh=True, user=user, session=session)

    assert result.subscribed is True


@pytest.mark.asyncio
async def test_exempt_user_passes_without_joining(session) -> None:
    await _channel(session)
    user = await _user(session)
    session.add(SubscriptionExemption(telegram_id=TG_ID, is_active=True))
    await session.flush()

    result = await api.get_subscription(fresh=False, user=user, session=session)

    assert result.subscribed is True


@pytest.mark.asyncio
async def test_referral_reward_waits_for_subscription(session) -> None:
    """Bot endi obuna so'ramaydi — mukofot shu tekshiruvga ko'chgan."""
    settings_row = await payment_service.get_settings(session)
    settings_row.referral_bonus = Decimal(1000)
    await _channel(session)
    inviter = await _user(session, 5001)
    invited = await _user(session, referred_by_id=inviter.id)

    # Obunasiz — mukofot yo'q.
    await api.get_subscription(fresh=False, user=invited, session=session)
    assert Decimal(str(inviter.balance or 0)) == Decimal(0)
    assert invited.referral_confirmed is False

    # Obuna bo'ldi — mukofot va xabar.
    _FakeBot.status = "member"
    await api.get_subscription(fresh=True, user=invited, session=session)
    await session.refresh(inviter)
    assert Decimal(str(inviter.balance)) == Decimal(1000)
    assert invited.referral_confirmed is True
    assert _FakeBot.sent == [5001]

    # Har qidiruvda chaqiriladi — pul takror berilmasligi kerak.
    await api.get_subscription(fresh=False, user=invited, session=session)
    await session.refresh(inviter)
    assert Decimal(str(inviter.balance)) == Decimal(1000)
