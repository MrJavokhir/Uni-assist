import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User
from app.i18n import t
from app.services import referral_service
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


async def entry_screen(bot, session: AsyncSession, user: User, full_name: str):
    """/start dan keyingi ekran: xush kelibsiz va Mini App tugmasi.

    (matn, klaviatura) qaytaradi. Majburiy kanal obunasi bu yerda EMAS —
    Mini App'da, onboarding oxirida "Find my programs" bosilganda so'raladi
    (app/webapp/api.py, `/subscription`); taklif mukofoti ham o'sha yerda.
    """
    lang = user.ui_language.value
    return t("start.welcome", lang, name=full_name), start_keyboard(lang)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, command: CommandObject) -> None:
    """/start -> xush kelibsiz (Mini App tugmasi). Obuna Mini App'da so'raladi.

    Til so'ralmaydi: yangi foydalanuvchi ingliz tilida boshlaydi va tilni
    Mini App'dagi Profil -> Til orqali almashtiradi. Ilgari birinchi qadam
    uch tilli til tanlash edi.

    Taklif havolasi (`/start ref123`) FAQAT birinchi kirishda hisobga
    olinadi, shuning uchun foydalanuvchi bor-yo'qligi yaratishdan OLDIN
    tekshiriladi: aks holda eski foydalanuvchi ham "taklif qilingan" bo'lib
    qolardi va do'stlar bir-birini taklif qilib pul yig'ishi mumkin edi.
    """
    is_new = (
        await session.execute(select(User.id).where(User.telegram_id == message.from_user.id))
    ).scalar_one_or_none() is None

    user = await get_or_create_user(
        session,
        message.from_user.id,
        message.from_user.username,
        language_code=message.from_user.language_code,
    )

    if is_new:
        referrer_id = referral_service.parse_payload(command.args)
        if referrer_id is not None:
            await referral_service.attach(session, user, referrer_id)
            await session.commit()

    text, markup = await entry_screen(message.bot, session, user, message.from_user.full_name)
    await message.answer(text, reply_markup=markup)
