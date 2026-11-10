"""Sovg'a qutisi: kimga chiqadi, ochilganda nima tushadi, qachon ishlatiladi.

* Quti userga faqat faol sovg'a bo'lsa va u hali quti ochmagan bo'lsa
  chiqadi (har bir userga bir marta).
* Ochilganda faol sovg'alardan biri `weight` bo'yicha tasodifan tanlanadi.
  Qiymatlar (`service_id`, `discount_percent`) userga nusxalanadi — admin
  sovg'ani keyin o'zgartirsa ham, va'da qilingani o'zgarmaydi.
* Sovg'a o'sha xizmat olinganda (qo'llanma) yoki so'rov yuborilganda
  (qo'lda bajariladigan xizmat) ishlatiladi va boshqa ishlamaydi.
"""

import random
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AdmissionService, Gift, User, UserGift


def _active_gifts():
    return (
        select(Gift)
        .join(Gift.service)
        .where(Gift.is_active.is_(True), AdmissionService.is_active.is_(True), Gift.weight > 0)
    )


async def gift_available(session: AsyncSession, user: User) -> bool:
    """Bosh sahifada quti ko'rsatilsinmi."""
    has_gift = await session.scalar(select(exists(_active_gifts())))
    if not has_gift:
        return False
    opened = await session.scalar(select(exists().where(UserGift.user_id == user.id)))
    return not opened


async def user_gift(session: AsyncSession, user: User) -> UserGift | None:
    return (
        await session.execute(
            select(UserGift)
            .options(selectinload(UserGift.service))
            .where(UserGift.user_id == user.id)
        )
    ).scalar_one_or_none()


async def open_gift(
    session: AsyncSession, user: User, rng: random.Random | None = None
) -> UserGift | None:
    """Qutini ochadi. Allaqachon ochilgan bo'lsa — o'sha sovg'a qaytadi.

    Faol sovg'a bo'lmasa None.
    """
    existing = await user_gift(session, user)
    if existing is not None:
        return existing
    gifts = (await session.execute(_active_gifts())).scalars().all()
    if not gifts:
        return None
    gift = (rng or random).choices(gifts, weights=[g.weight for g in gifts], k=1)[0]
    session.add(
        UserGift(
            user_id=user.id,
            gift_id=gift.id,
            service_id=gift.service_id,
            discount_percent=gift.discount_percent,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        # Ikki marta tez bosildi — birinchisi yozib ulgurdi.
        await session.rollback()
    return await user_gift(session, user)


async def unused_gift_for(session: AsyncSession, user: User, service_id: int) -> UserGift | None:
    """Shu xizmat uchun hali ishlatilmagan sovg'a."""
    gift = await user_gift(session, user)
    if gift is None or gift.used_at is not None or gift.service_id != service_id:
        return None
    return gift


def discounted(price: Decimal, percent: int) -> Decimal:
    """Chegirmadan keyingi narx (butun songa yaxlitlanadi; 100% — 0)."""
    percent = max(0, min(100, percent))
    value = price * (100 - percent) / 100
    return value.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def mark_used(gift: UserGift) -> None:
    gift.used_at = datetime.now(UTC)
