"""Majburiy kanal obunasini tekshirish.

Admin panelda kanal havolasi kiritiladi, bot esa foydalanuvchi o'sha kanal(lar)ga
a'zo ekanini `getChatMember` orqali tekshiradi. Har bir so'rovda Telegram API'ga
murojaat qilmaslik uchun natija Redis'da qisqa muddatga keshlanadi.

Tekshiruv FAQAT bot tomonida (app/bot/middlewares.py) bo'ladi: /start bosilganda
obuna so'raladi, Mini App tugmasi esa undan keyin beriladi. Mini App ichida
qayta to'sib turish foydalanuvchini ikki marta to'xtatardi.

MUHIM: tekshiruv ishlashi uchun bot kanalda administrator bo'lishi shart. Agar
bot kanalga kira olmasa (admin emas, kanal o'chirilgan, chat_id noto'g'ri), biz
foydalanuvchini BLOKLAMAYMIZ — noto'g'ri sozlama hammani ichkariga kirita
olmay qo'yishidan ko'ra, o'tkazib yuborgan yaxshiroq (fail-open).
"""

import logging
import re
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RequiredChannel

logger = logging.getLogger(__name__)

# A'zolikni tasdiqlovchi holatlar ("left" va "kicked" — a'zo emas)
MEMBER_STATUSES = {"creator", "administrator", "member", "restricted"}

# Kesh muddati: obuna holati tez-tez o'zgarmaydi, lekin foydalanuvchi obuna
# bo'lgach uzoq kutib qolmasligi kerak. "Tekshirish" tugmasi keshni tozalaydi.
CACHE_TTL_SECONDS = 300

_PUBLIC_LINK = re.compile(r"(?:https?://)?(?:t\.me|telegram\.me)/(?!\+|joinchat/)([A-Za-z0-9_]{4,})")
_NUMERIC_ID = re.compile(r"^-?\d{5,}$")
_USERNAME = re.compile(r"^[A-Za-z0-9_]{4,}$")


@dataclass
class ChannelInfo:
    title: str
    invite_url: str


def derive_chat_id(invite_url: str) -> str | None:
    """Ochiq kanal havolasidan "@kanalnomi" ni chiqaradi.

    Yopiq kanallar (t.me/+... yoki t.me/joinchat/...) uchun None qaytaradi —
    ular uchun admin raqamli chat_id ni qo'lda kiritishi kerak.
    """
    match = _PUBLIC_LINK.search(invite_url or "")
    return f"@{match.group(1)}" if match else None


def normalize_chat_id(value: str | None) -> str | None:
    """Admin kiritgan qiymatni Telegram API kutadigan ko'rinishga keltiradi.

    Telegram faqat "@kanalnomi" yoki raqamli ID ni tushunadi. Admin esa
    odatda Chat ID maydoniga to'liq havolani ("https://t.me/kanal") yoki
    "@"siz nomni yozib qo'yadi — ilgari bunday qiymat o'zgartirilmasdan
    uzatilar va Telegram "chat not found" qaytarardi. Natijada majburiy
    obuna jimgina ishlamay qolardi.

    Yopiq kanal havolasidan (t.me/+..., joinchat/...) username chiqmaydi,
    shuning uchun None qaytadi — bunday kanal uchun raqamli ID kerak.
    """
    raw = (value or "").strip()
    if not raw:
        return None
    if _NUMERIC_ID.match(raw):
        return raw
    derived = derive_chat_id(raw)
    if derived:
        return derived
    if raw.startswith("@") and _USERNAME.match(raw[1:]):
        return raw
    if _USERNAME.match(raw):
        return f"@{raw}"
    return None


async def verify_channel_access(bot: Bot, chat_id: str) -> str | None:
    """Bot shu kanalda a'zolikni tekshira oladimi.

    Xato matnini qaytaradi (admin ko'radi), hammasi joyida bo'lsa — None.
    Ataylab aynan `get_chat_member` sinaladi: `get_chat` bot admin bo'lmasa
    ham ishlayveradi, a'zolikni o'qish esa adminlikni talab qiladi.
    """
    try:
        await bot.get_chat_member(chat_id, bot.id)
    except TelegramForbiddenError:
        return f"Bot {chat_id} kanaliga kira olmaydi. Botni kanalga administrator qilib qo'shing."
    except TelegramBadRequest as err:
        return (
            f"Telegram {chat_id} bo'yicha javob berdi: {err.message}. "
            "Kanal nomi to'g'riligini va bot o'sha kanalda administrator ekanini tekshiring."
        )
    except TelegramAPIError:
        # Tarmoq yoki vaqtinchalik xato — saqlashga to'sqinlik qilmaymiz.
        logger.exception("Kanalni tekshirib bo'lmadi: %s", chat_id)
        return None
    return None


async def active_channels(session: AsyncSession) -> list[RequiredChannel]:
    stmt = (
        select(RequiredChannel)
        .where(RequiredChannel.is_active.is_(True))
        .order_by(RequiredChannel.id)
    )
    return list((await session.execute(stmt)).scalars().all())


def _cache_key(telegram_id: int | str) -> str:
    return f"subscribed:{telegram_id}"


async def clear_cache(redis: Redis, telegram_id: int) -> None:
    try:
        await redis.delete(_cache_key(telegram_id))
    except Exception:
        logger.exception("Obuna keshini tozalashda xatolik")


async def clear_all_cache(redis: Redis | None) -> None:
    """Admin kanallar ro'yxatini o'zgartirganda chaqiriladi — aks holda eski
    "obuna bo'lgan" natija 5 daqiqagacha kuchda qolardi."""
    if redis is None:
        return
    try:
        async for key in redis.scan_iter(match=_cache_key("*")):
            await redis.delete(key)
    except Exception:
        logger.exception("Obuna keshini to'liq tozalashda xatolik")


async def missing_channels(
    bot: Bot,
    session: AsyncSession,
    redis: Redis | None,
    telegram_id: int,
    *,
    use_cache: bool = True,
) -> list[ChannelInfo]:
    """Foydalanuvchi obuna bo'lmagan kanallar ro'yxati (bo'sh bo'lsa — hammasi joyida)."""
    channels = await active_channels(session)
    if not channels:
        return []

    if use_cache and redis is not None:
        try:
            if await redis.get(_cache_key(telegram_id)) == "1":
                return []
        except Exception:
            logger.exception("Obuna keshini o'qishda xatolik")

    missing: list[ChannelInfo] = []
    for channel in channels:
        # Bazada allaqachon noto'g'ri saqlangan qiymat ham shu yerda
        # tuzatiladi — adminning qo'lda tahrirlashini kutmaymiz.
        chat_id = normalize_chat_id(channel.chat_id) or derive_chat_id(channel.invite_url)
        if not chat_id:
            # Yopiq kanal uchun chat_id kiritilmagan — tekshirib bo'lmaydi.
            logger.warning("Kanal uchun chat_id aniqlanmadi: %s", channel.title)
            continue

        try:
            member = await bot.get_chat_member(chat_id, telegram_id)
        except TelegramAPIError:
            # Bot kanalda admin emas yoki chat_id noto'g'ri — bloklamaymiz.
            logger.exception("Kanal a'zoligini tekshirib bo'lmadi: %s", chat_id)
            continue

        if member.status not in MEMBER_STATUSES:
            missing.append(ChannelInfo(title=channel.title, invite_url=channel.invite_url))

    if not missing and redis is not None:
        try:
            await redis.set(_cache_key(telegram_id), "1", ex=CACHE_TTL_SECONDS)
        except Exception:
            logger.exception("Obuna keshini yozishda xatolik")

    return missing
