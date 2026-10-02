"""Bo'sh suhbatda ko'rinadigan bot tavsifi.

Matnlar Telegram chegarasidan oshmasligi SHART: oshsa, Telegram butun
so'rovni rad etadi va bot tavsifsiz qolaveradi — bu esa faqat prodda,
jimgina bilinardi.
"""

import pytest
from aiogram.exceptions import TelegramAPIError

from app.bot.profile_setup import apply_bot_profile
from app.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, t

# Telegram Bot API chegaralari.
DESCRIPTION_LIMIT = 512
SHORT_DESCRIPTION_LIMIT = 120


class _FakeBot:
    def __init__(self, fail: bool = False) -> None:
        self.descriptions: list[tuple[str | None, str]] = []
        self.short_descriptions: list[tuple[str | None, str]] = []
        self.fail = fail

    async def set_my_description(self, description: str, language_code: str | None = None):
        if self.fail:
            raise TelegramAPIError(method=None, message="xato")
        self.descriptions.append((language_code, description))

    async def set_my_short_description(
        self, short_description: str, language_code: str | None = None
    ):
        if self.fail:
            raise TelegramAPIError(method=None, message="xato")
        self.short_descriptions.append((language_code, short_description))


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_texts_fit_telegram_limits(lang: str) -> None:
    assert len(t("bot.description", lang)) <= DESCRIPTION_LIMIT
    assert len(t("bot.short_description", lang)) <= SHORT_DESCRIPTION_LIMIT


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_texts_are_translated(lang: str) -> None:
    """Kalit topilmasa `t()` kalitning o'zini qaytaradi — bu holat o'tmasin."""
    assert t("bot.description", lang) != "bot.description"
    assert t("bot.short_description", lang) != "bot.short_description"


@pytest.mark.asyncio
async def test_profile_is_set_for_every_language() -> None:
    bot = _FakeBot()

    await apply_bot_profile(bot)

    languages = [code for code, _ in bot.descriptions]
    # `None` — sukut bo'yicha matn: Telegram tili ro'yxatda bo'lmagan
    # hammaga shu ko'rinadi.
    assert languages == [None, *SUPPORTED_LANGUAGES]
    assert [code for code, _ in bot.short_descriptions] == languages


@pytest.mark.asyncio
async def test_default_text_is_uzbek() -> None:
    """Asosiy auditoriya o'zbek tilida — sukut ham shunday bo'lishi kerak."""
    bot = _FakeBot()

    await apply_bot_profile(bot)

    default_text = dict(bot.descriptions)[None]
    assert default_text == t("bot.description", DEFAULT_LANGUAGE)


@pytest.mark.asyncio
async def test_api_error_does_not_stop_the_bot() -> None:
    """Tavsif — bezak. U yetkazilmagani uchun bot javob bermay qolmasin."""
    bot = _FakeBot(fail=True)

    await apply_bot_profile(bot)

    assert bot.descriptions == []
