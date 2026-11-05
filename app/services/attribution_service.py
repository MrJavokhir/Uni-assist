"""Atributsiya: foydalanuvchi qaysi manbadan kelgani va deep link maqsadi.

Qoidalar:
  * `first_source`, `first_param_raw`, `first_seen_at` — faqat BIRINCHI
    kirishda yoziladi va keyin hech qachon ustidan yozilmaydi;
  * `last_source` — har bir kirishda (/start yoki `startapp` havolasi);
  * taklif qilgan odam — faqat YANGI foydalanuvchiga, bir marta. Bunda
    mavjud referal tizimi ishlatiladi (`referral_service.attach`):
    o'zini taklif qilish va mavjud bo'lmagan referrer o'sha yerda rad etiladi;
  * deep link ochishi kerak bo'lgan ekran `pending_target`ga 24 soatga
    saqlanadi va Mini App o'sha ekranga yetganda tozalanadi. Shunda kanalga
    o'tib qaytgan yoki ilovani keyinroq menyu tugmasidan ochgan odam ham
    reklamada va'da qilingan ekranga tushadi.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services import referral_service
from app.services.deeplink import SCREEN_HOME, SCREEN_PROGRAMS, StartParam, resolve_target

logger = logging.getLogger(__name__)

PENDING_TTL = timedelta(hours=24)

# Bu ekranlar natijalarni ko'rsatadi — hozirgi "Find my programs" kabi
# avval majburiy kanal so'raladi. Dastur/grant sahifasi esa ochiq.
GATED_SCREENS = frozenset({SCREEN_PROGRAMS})


def needs_gate(target: dict[str, Any] | None) -> bool:
    return bool(target) and target.get("screen") in GATED_SCREENS


async def record_entry(
    session: AsyncSession,
    user: User,
    parsed: StartParam,
    *,
    is_new: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Kirishni qayd qiladi va ochilishi kerak bo'lgan ekranni qaytaradi.

    `is_new` — foydalanuvchi aynan shu kirishda yaratilganmi. Taklif faqat
    shunda bog'lanadi: aks holda eski foydalanuvchi ham "taklif qilingan"
    bo'lib qolardi va do'stlar bir-birini taklif qilib pul yig'ishi mumkin edi.
    Xato bo'lsa ham oqim to'xtamaydi — home qaytadi.
    """
    now = now or datetime.now(UTC)
    target: dict[str, Any] = {"screen": SCREEN_HOME}
    if not parsed.counts_for_attribution:
        return target
    try:
        if user.first_seen_at is None:
            user.first_source = parsed.source
            user.first_param_raw = parsed.raw
            user.first_seen_at = now
            if is_new and parsed.referrer_id is not None:
                await referral_service.attach(session, user, parsed.referrer_id)
        user.last_source = parsed.source

        target = await resolve_target(session, parsed)
        if target.get("screen") == SCREEN_HOME:
            # Yangi kirish eski va'dani bekor qiladi (oxirgi niyat amal qiladi).
            user.pending_target = None
            user.pending_target_expires_at = None
        else:
            user.pending_target = target
            user.pending_target_expires_at = now + PENDING_TTL
        await session.commit()
    except Exception:
        logger.exception("Atributsiyani yozib bo'lmadi: %s", user.id)
        await session.rollback()
    return target


def pending_target(user: User, now: datetime | None = None) -> dict[str, Any] | None:
    """Amaldagi (muddati o'tmagan) maqsad yoki None."""
    now = now or datetime.now(UTC)
    if not user.pending_target or user.pending_target_expires_at is None:
        return None
    if user.pending_target_expires_at <= now:
        return None
    return dict(user.pending_target)


async def clear_pending(session: AsyncSession, user: User) -> None:
    if user.pending_target is None and user.pending_target_expires_at is None:
        return
    user.pending_target = None
    user.pending_target_expires_at = None
    await session.commit()
