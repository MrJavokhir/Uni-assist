"""Taklif (referal) dasturi: havola, bog'lash va mukofot.

Oqim:
    1. Foydalanuvchi o'z havolasini ulashadi: t.me/<bot>?start=ref<telegram_id>
    2. Yangi odam /start bosadi -> `attach()` "kim taklif qilgan"ni yozadi.
       Pul HALI berilmaydi.
    3. Yangi odam majburiy kanalga obuna bo'lgach -> `reward()` taklif
       qilgan odamning balansiga mukofot qo'shadi.

Nega mukofot darhol emas, obunadan keyin: aks holda soxta akkauntlar
bilan pul yig'ish arzon bo'lardi. Obuna talabi ham to'siq bo'ladi, ham
taklifni haqiqiy foydali qiladi — kanalga odam qo'shiladi.

Taklif BIR MARTA tasdiqlanadi. Buni `users.referral_confirmed` bayrog'i
ta'minlaydi va u shartli UPDATE bilan yoqiladi: "Tekshirish" tugmasi bir
necha marta bosilsa ham pul takror berilmaydi.

Tasdiqlangan taklif ikki narsaga ishlaydi: mukofot (agar summa 0 dan
katta bo'lsa) va Admission Kit xizmatlarini pulsiz ochish.
"""

import logging
import re
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.i18n import t
from app.services import payment_service

logger = logging.getLogger(__name__)

# `/start` payload'i: "ref" + taklif qilgan odamning telegram_id'si.
# Telegram payload'ga faqat harf, raqam, "_" va "-" ruxsat beradi.
_PAYLOAD = re.compile(r"^ref(\d{3,20})$")
PREFIX = "ref"


def build_payload(telegram_id: int) -> str:
    return f"{PREFIX}{telegram_id}"


def build_link(bot_username: str | None, telegram_id: int) -> str | None:
    if not bot_username:
        return None
    return f"https://t.me/{bot_username}?start={build_payload(telegram_id)}"


def parse_payload(payload: str | None) -> int | None:
    """`/start` argumentidan taklif qilgan odamning telegram_id'si."""
    match = _PAYLOAD.match((payload or "").strip())
    return int(match.group(1)) if match else None


async def attach(session: AsyncSession, user: User, referrer_telegram_id: int) -> bool:
    """Yangi foydalanuvchini taklif qilgan odamga bog'laydi.

    Chaqiruvchi foydalanuvchi AYNAN HOZIR yaratilganini tekshirishi kerak:
    bu yerda eski foydalanuvchi ham bog'lanib qolishi mumkin bo'lardi va
    "eski do'stlarni taklif qilib" pul yig'ish yo'li ochilardi.
    """
    if user.referred_by_id is not None:
        return False
    if referrer_telegram_id == user.telegram_id:
        # O'zini o'zi taklif qilish.
        return False

    referrer = (
        await session.execute(select(User).where(User.telegram_id == referrer_telegram_id))
    ).scalar_one_or_none()
    if referrer is None or referrer.id == user.id:
        return False

    user.referred_by_id = referrer.id
    await session.flush()
    logger.info("Taklif: %s -> %s", referrer.telegram_id, user.telegram_id)
    return True


async def reward(session: AsyncSession, user: User) -> tuple[User, Decimal] | None:
    """Taklifni tasdiqlaydi va mukofot beradi. Pul berilgan bo'lsa (kim, qancha).

    TASDIQLASH va PUL BERISH ikki boshqa narsa:
      * tasdiqlash — har doim bo'ladi (odam kanalga a'zo bo'ldi). Taklif
        shundan keyin xizmat ochish uchun sanaladi;
      * pul — faqat mukofot summasi 0 dan katta bo'lsa.

    Ilgari ikkalasi bitta shart ostida edi: mukofot 0 ga qo'yilsa bayroq
    yoqilmay, taklif hech qayerda hisobga olinmay qolardi.

    Hech narsa qilmaydigan holatlar: foydalanuvchi taklif bilan kelmagan
    yoki taklif allaqachon tasdiqlangan.
    """
    if user.referred_by_id is None or user.referral_confirmed:
        return None

    # Shartli UPDATE: tugma bir necha marta bosilsa ham faqat bittasi
    # qator o'zgartira oladi, demak tasdiq ham, pul ham bir marta.
    result = await session.execute(
        update(User)
        .where(User.id == user.id, User.referral_confirmed.is_(False))
        .values(referral_confirmed=True)
    )
    if result.rowcount != 1:
        return None
    # Sessiyadagi nusxa eskirmasin — keyin unga qarab qaror qabul
    # qilinishi mumkin.
    await session.refresh(user)

    referrer = await session.get(User, user.referred_by_id)
    if referrer is None:
        return None

    settings_row = await payment_service.get_settings(session)
    amount = Decimal(str(settings_row.referral_bonus or 0))
    if amount <= 0:
        # Dastur pulsiz ishlayapti: taklif tasdiqlandi (xizmat ochish
        # uchun sanaladi), lekin balansga hech narsa qo'shilmaydi.
        logger.info("Taklif tasdiqlandi, mukofot 0: %s", user.telegram_id)
        return None

    await payment_service.reward_referral(
        session,
        referrer,
        amount,
        note=f"Taklif: @{user.username}" if user.username else "Taklif qilingan do'st",
    )
    logger.info("Taklif mukofoti: %s -> %s, %s", user.telegram_id, referrer.telegram_id, amount)
    return referrer, amount


async def count_invited(session: AsyncSession, user: User) -> int:
    """Nechta TASDIQLANGAN taklif bor.

    Faqat kanalga a'zo bo'lganlar sanaladi. Shunchaki havolani bosib,
    keyin ketib qolgan odam na mukofot beradi, na xizmat ochadi — aks
    holda soxta akkauntlar bilan xizmat ochib olish arzon bo'lardi.
    """
    stmt = select(func.count(User.id)).where(
        User.referred_by_id == user.id, User.referral_confirmed.is_(True)
    )
    return (await session.execute(stmt)).scalar_one()


async def reward_and_notify(session: AsyncSession, bot, user: User) -> None:
    """Mukofot beradi va taklif qilgan odamga xabar yuboradi.

    Obuna tasdiqlangan ikki joydan chaqiriladi (til tanlangandan keyin va
    "Tekshirish" tugmasidan keyin), shuning uchun mantiq shu yerda — ikki
    joyda takrorlanib, biri o'zgarib ikkinchisi qolib ketmasligi uchun.
    """
    result = await reward(session, user)
    if result is None:
        return

    referrer, amount = result
    settings_row = await payment_service.get_settings(session)
    currency = settings_row.currency
    lang = referrer.ui_language.value
    text = t(
        "referral.earned",
        lang,
        amount=f"{amount:,.0f} {currency}",
        balance=f"{Decimal(str(referrer.balance or 0)):,.0f} {currency}",
    )
    try:
        await bot.send_message(referrer.telegram_id, text)
    except Exception:
        logger.exception("Taklif mukofoti haqida xabar yetmadi: %s", referrer.telegram_id)
