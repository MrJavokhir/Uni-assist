import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import language_keyboard
from app.config import settings
from app.i18n import t
from app.services.user_service import get_or_create_user

router = Router(name="start")

# Til hali tanlanmagani uchun uchala tilda ham yoziladi.
CHOOSE_LANGUAGE = "Tilni tanlang · Выберите язык · Choose your language"

# Telegram Mini App'ning statik fayllarini agressiv keshlaydi va yangi deploy
# foydalanuvchiga yetib bormaydi. Har ishga tushishda URL'ga yangi "v" qo'shamiz —
# Telegram uchun bu butunlay yangi manzil, shuning uchun kesh chetlab o'tiladi.
_BUILD_ID = str(int(time.time()))


def webapp_url() -> str:
    parts = urlparse(settings.webapp_url)
    query = dict(parse_qsl(parts.query))
    query["v"] = _BUILD_ID
    return urlunparse(parts._replace(query=urlencode(query)))


def start_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Mini App'ni ochish tugmasi (obuna tasdiqlangach ham shu ko'rsatiladi)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("start.open_app", lang),
                    web_app=WebAppInfo(url=webapp_url()),
                )
            ]
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """/start — birinchi qadam har doim til tanlash.

    Obuna tekshiruvi ham, xush kelibsiz xabari ham tildan keyin bo'ladi:
    aks holda foydalanuvchi o'zi tushunmaydigan tilda kanal so'rovini
    ko'rardi. /start qayta berilsa tilni almashtirish imkonini ham beradi.
    """
    await get_or_create_user(
        session,
        message.from_user.id,
        message.from_user.username,
        language_code=message.from_user.language_code,
    )
    await message.answer(CHOOSE_LANGUAGE, reply_markup=language_keyboard())
