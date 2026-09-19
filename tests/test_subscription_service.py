import pytest
from aiogram.exceptions import TelegramAPIError

from app.db.models import RequiredChannel
from app.services.subscription_service import derive_chat_id, missing_channels


class _FakeMember:
    def __init__(self, status: str) -> None:
        self.status = status


class _FakeBot:
    """`get_chat_member` ni taqlid qiladi: chat_id -> status yoki Exception."""

    def __init__(self, statuses: dict[str, str | Exception]) -> None:
        self.statuses = statuses
        self.calls: list[tuple[str, int]] = []

    async def get_chat_member(self, chat_id: str, user_id: int):
        self.calls.append((chat_id, user_id))
        result = self.statuses[chat_id]
        if isinstance(result, Exception):
            raise result
        return _FakeMember(result)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://t.me/uniassist_uz", "@uniassist_uz"),
        ("http://t.me/uniassist_uz", "@uniassist_uz"),
        ("t.me/uniassist_uz", "@uniassist_uz"),
        ("https://telegram.me/uniassist_uz", "@uniassist_uz"),
        ("https://t.me/uniassist_uz/", "@uniassist_uz"),
        # Yopiq kanallar — username yo'q, admin raqamli ID kiritishi kerak
        ("https://t.me/+AbCdEf123456", None),
        ("https://t.me/joinchat/AbCdEf123456", None),
        ("", None),
        ("shunchaki matn", None),
    ],
)
def test_derive_chat_id(url: str, expected: str | None) -> None:
    assert derive_chat_id(url) == expected


async def _add_channel(session, **kwargs) -> RequiredChannel:
    channel = RequiredChannel(
        title=kwargs.pop("title", "Kanal"),
        invite_url=kwargs.pop("invite_url", "https://t.me/uniassist_uz"),
        **kwargs,
    )
    session.add(channel)
    await session.commit()
    return channel


@pytest.mark.asyncio
async def test_no_channels_means_no_gate(session) -> None:
    bot = _FakeBot({})
    assert await missing_channels(bot, session, None, 1) == []
    assert bot.calls == []


@pytest.mark.asyncio
async def test_subscribed_user_passes(session) -> None:
    await _add_channel(session)
    bot = _FakeBot({"@uniassist_uz": "member"})
    assert await missing_channels(bot, session, None, 42) == []


@pytest.mark.asyncio
async def test_unsubscribed_user_is_blocked(session) -> None:
    await _add_channel(session, title="Uni Assist")
    bot = _FakeBot({"@uniassist_uz": "left"})

    missing = await missing_channels(bot, session, None, 42)

    assert [c.title for c in missing] == ["Uni Assist"]
    assert missing[0].invite_url == "https://t.me/uniassist_uz"


@pytest.mark.asyncio
async def test_inactive_channel_is_ignored(session) -> None:
    await _add_channel(session, is_active=False)
    bot = _FakeBot({"@uniassist_uz": "left"})
    assert await missing_channels(bot, session, None, 42) == []


@pytest.mark.asyncio
async def test_explicit_chat_id_wins_over_url(session) -> None:
    await _add_channel(session, invite_url="https://t.me/+Secret", chat_id="-1001234567890")
    bot = _FakeBot({"-1001234567890": "left"})

    missing = await missing_channels(bot, session, None, 42)

    assert len(missing) == 1
    assert bot.calls == [("-1001234567890", 42)]


@pytest.mark.asyncio
async def test_api_error_does_not_block_user(session) -> None:
    """Bot kanalda admin bo'lmasa hammani bloklab qo'ymasligi kerak (fail-open)."""
    await _add_channel(session)
    bot = _FakeBot({"@uniassist_uz": TelegramAPIError(method=None, message="not admin")})

    assert await missing_channels(bot, session, None, 42) == []


@pytest.mark.asyncio
async def test_private_channel_without_chat_id_is_skipped(session) -> None:
    await _add_channel(session, invite_url="https://t.me/+Secret")
    bot = _FakeBot({})
    assert await missing_channels(bot, session, None, 42) == []
