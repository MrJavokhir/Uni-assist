import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.i18n import t
from app.services.user_service import get_or_create_user

router = Router(name="start")

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
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    lang = user.ui_language.value

    await message.answer(
        t("start.welcome", lang, name=message.from_user.full_name),
        reply_markup=start_keyboard(lang),
    )
