import pytest
from aiogram.exceptions import TelegramAPIError

from app.db.models import RequiredChannel
from app.services.subscription_service import (
    derive_chat_id,
    missing_channels,
    normalize_chat_id,
)


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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Asosiy holat: admin Chat ID maydoniga to'liq havolani yozib qo'ygan.
        # Ilgari shu qiymat o'zgartirilmasdan Telegram'ga uzatilar va
        # "chat not found" qaytarardi — majburiy obuna jimgina ishlamasdi.
        ("https://t.me/javokhir_frames", "@javokhir_frames"),
        ("t.me/uniassist_uz", "@uniassist_uz"),
        ("telegram.me/some_channel", "@some_channel"),
        ("  https://t.me/uniassist_uz  ", "@uniassist_uz"),
        # "@"siz yozilgan nom
        ("uniassist_uz", "@uniassist_uz"),
        # To'g'ri kiritilgan qiymatlar o'zgarmaydi
        ("@uniassist_uz", "@uniassist_uz"),
        ("-1001234567890", "-1001234567890"),
        # Aniqlab bo'lmaydiganlar
        ("https://t.me/+AbCdEf123456", None),
        ("https://t.me/joinchat/AbCdEf123456", None),
        ("@x", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_chat_id(raw: str | None, expected: str | None) -> None:
    assert normalize_chat_id(raw) == expected


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
async def test_link_stored_in_chat_id_is_normalized(session) -> None:
    """Productionda aynan shunday bo'lgan: admin Chat ID maydoniga havolani
    yozgan, Telegram esa uni tanimay "chat not found" qaytargan va majburiy
    obuna jimgina ishlamay qolgan."""
    await _add_channel(session, chat_id="https://t.me/javokhir_frames")
    bot = _FakeBot({"@javokhir_frames": "left"})

    missing = await missing_channels(bot, session, None, 42)

    assert len(missing) == 1
    assert bot.calls == [("@javokhir_frames", 42)]


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
