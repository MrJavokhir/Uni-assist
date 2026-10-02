"""Bot profili: bo'sh suhbatda ko'rinadigan tavsif.

Odam botni birinchi marta ochganda faqat "Start" tugmasi va bo'sh ekran
ko'rinardi — bot nima qilishini tushuntiradigan hech narsa yo'q edi.
Telegram shu joyda bot TAVSIFINI ko'rsatadi ("What can this bot do?").

Ikki xil matn bor va ular boshqa-boshqa joyda chiqadi:
    description        -> bo'sh suhbatda, Start tugmasi ustida (512 belgi)
    short_description  -> bot profilida, nom ostida (120 belgi)

Matn har deployda qayta yuboriladi. Telegram bir xil qiymatni qayta
yozishdan shikoyat qilmaydi, alohida "o'zgardimi" tekshiruvi esa ikki
barobar ko'p so'rov degani bo'lardi.

TAVSIF TEPASIDAGI RASM/GIF bu yerdan qo'yilmaydi: Bot API'da unday
usul yo'q, u faqat @BotFather orqali yuklanadi
(/mybots -> bot -> Bot Settings -> Description Picture).
"""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, t

logger = logging.getLogger(__name__)


async def apply_bot_profile(bot: Bot) -> None:
    """Tavsiflarni Telegram'ga yuboradi.

    Xatolik botni ishga tushishdan TO'XTATMAYDI: tavsif — bezak, u
    yetkazilmagani uchun bot javob bermay qolishi mantiqsiz bo'lardi.
    """
    # `None` — sukut bo'yicha matn: Telegram tili ro'yxatda bo'lmagan
    # hammaga shu ko'rinadi. O'zbek tili asosiy auditoriya, shuning uchun
    # sukut ham o'zbekcha.
    for language_code in (None, *SUPPORTED_LANGUAGES):
        lang = language_code or DEFAULT_LANGUAGE
        try:
            await bot.set_my_description(
                description=t("bot.description", lang),
                language_code=language_code,
            )
            await bot.set_my_short_description(
                short_description=t("bot.short_description", lang),
                language_code=language_code,
            )
        except TelegramAPIError:
            logger.exception("Bot tavsifini yangilab bo'lmadi: til=%s", language_code or "default")
