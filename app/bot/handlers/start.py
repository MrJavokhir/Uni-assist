import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.payment import cmd_topup
from app.config import settings
from app.db.models import User
from app.i18n import t
from app.services import attribution_service, event_service
from app.services.deeplink import parse_start_param
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


async def entry_screen(
    bot, session: AsyncSession, user: User, full_name: str, lang: str | None = None
):
    """/start dan keyingi ekran: xush kelibsiz va Mini App tugmasi.

    (matn, klaviatura) qaytaradi. Majburiy kanal obunasi bu yerda EMAS —
    Mini App'da, onboarding oxirida "Find my programs" bosilganda so'raladi
    (app/webapp/api.py, `/subscription`); taklif mukofoti ham o'sha yerda.

    `lang` berilmasa foydalanuvchining o'z tili ishlatiladi.
    """
    lang = lang or user.ui_language.value
    return t("start.welcome", lang, name=full_name), start_keyboard(lang)


# Mini App'dagi "Top up" tugmasi botni `?start=topup` bilan ochadi — to'ldirish
# darhol boshlanadi (foydalanuvchi /topup yozishi shart emas).
TOPUP_PAYLOAD = "topup"

# Yangi foydalanuvchiga birinchi xabar Telegram tilidan qat'i nazar shu tilda.
NEW_USER_WELCOME_LANGUAGE = "uz"


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    command: CommandObject,
    state: FSMContext | None = None,
) -> None:
    """/start -> xush kelibsiz (Mini App tugmasi). Obuna Mini App'da so'raladi.

    Til so'ralmaydi: yangi foydalanuvchi xush kelibsiz xabarini o'zbekcha
    oladi, Mini App esa ingliz tilida boshlanadi va til Profil -> Til orqali
    almashtiriladi. Keyingi /start lar foydalanuvchining o'z tilida.

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

    # Deep link: manba (atributsiya), taklif qilgan odam va ochiladigan
    # ekran (`pending_target`). Mini App ochilganda o'sha ekranga olib
    # boradi — kanal tekshiruvidan keyin ham (app/services/attribution_service.py).
    parsed = parse_start_param(command.args)
    await attribution_service.record_entry(session, user, parsed, is_new=is_new)
    await event_service.log(
        session,
        user,
        event_service.START,
        {"param": parsed.raw} if parsed.raw else None,
        source=parsed.source,
    )

    if state is not None and (command.args or "").strip() == TOPUP_PAYLOAD:
        await cmd_topup(message, session, state)
        return

    text, markup = await entry_screen(
        message.bot,
        session,
        user,
        message.from_user.full_name,
        lang=NEW_USER_WELCOME_LANGUAGE if is_new else None,
    )
    await message.answer(text, reply_markup=markup)
