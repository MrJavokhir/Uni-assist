"""Foydalanuvchi hodisalari (`events` jadvali).

Asosiy qoida: hodisani yozish oqimni HECH QACHON buzmaydi va sezilarli
sekinlashtirmaydi. Yozuv alohida SAVEPOINT ichida qilinadi — u yiqilsa
faqat o'sha savepoint bekor bo'ladi, chaqiruvchining tranzaksiyasi
"buzilgan" holatda qolmaydi; xato log qilinadi va davom etiladi.

Bir martalik hodisalar (`ONCE_EVENTS`) bazadagi qisman unique indeks bilan
himoyalangan va `ON CONFLICT DO NOTHING` bilan yoziladi — ikki marta
bosilgan tugma yoki parallel so'rov ikkinchi qator yarata olmaydi.

Shaxsiy ma'lumot yozilmaydi: ism, telefon, xabar matni yo'q — faqat
foydalanuvchining ichki ID'si va hodisa xususiyatlari (dastur ID'si va h.k.).
"""

import logging
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event, User
from app.db.models.analytics import ONCE_EVENTS
from app.services.timezone_utils import TASHKENT_TZ

logger = logging.getLogger(__name__)

START = "start"
GATE_SHOWN = "gate_shown"
GATE_PASSED = "gate_passed"
APP_OPENED = "app_opened"
FILTER_COMPLETED = "filter_completed"
FIRST_SAVE = "first_save"
SAVE = "save"
PROGRAM_VIEWED = "program_viewed"
GRANT_VIEWED = "grant_viewed"
SHARE_CLICKED = "share_clicked"

# Mini App `POST /api/webapp/events` orqali faqat shularni yubora oladi.
# Qolganlari (start, kanal, filtr, saqlash) serverning o'zida, amal
# bajarilgan joyda yoziladi — ularni mijoz soxtalashtira olmasin.
CLIENT_EVENTS = frozenset({PROGRAM_VIEWED, GRANT_VIEWED, SHARE_CLICKED})

# Faollik (D1/D7 hisobi uchun).
ACTIVITY_EVENTS = (START, APP_OPENED)


def tashkent_day_bounds(day) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=TASHKENT_TZ)
    return start, start + timedelta(days=1)


async def log(
    session: AsyncSession,
    user: User | int,
    name: str,
    props: dict[str, Any] | None = None,
    *,
    source: str | None = None,
    commit: bool = True,
) -> bool:
    """Hodisani yozadi. Yozilgan bo'lsa True (bir martalik takrorida False)."""
    try:
        user_id = user if isinstance(user, int) else user.id
        if source is None and not isinstance(user, int):
            source = user.last_source
        stmt = insert(Event).values(user_id=user_id, name=name, source=source, props=props or None)
        if name in ONCE_EVENTS:
            stmt = stmt.on_conflict_do_nothing()
        async with session.begin_nested():
            result = await session.execute(stmt)
        if commit:
            await session.commit()
        return bool(result.rowcount)
    except Exception:
        logger.exception("Hodisani yozib bo'lmadi: %s", name)
        return False


async def log_daily(
    session: AsyncSession, user: User, name: str, now: datetime | None = None, **kwargs
) -> bool:
    """Hodisani Toshkent kuni bo'yicha kuniga ko'pi bilan bir marta yozadi
    (`app_opened`: Mini App kun davomida o'nlab marta ochilishi mumkin)."""
    try:
        now = now or datetime.now(UTC)
        day_start, day_end = tashkent_day_bounds(now.astimezone(TASHKENT_TZ).date())
        exists = (
            await session.execute(
                select(Event.id)
                .where(
                    Event.user_id == user.id,
                    Event.name == name,
                    Event.created_at >= day_start,
                    Event.created_at < day_end,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
    except Exception:
        logger.exception("Hodisa tekshiruvi yiqildi: %s", name)
        return False
    if exists is not None:
        return False
    return await log(session, user, name, **kwargs)


def filter_is_complete(user: User) -> bool:
    """Profilda daraja + yo'nalish + kamida bitta davlat bormi."""
    return bool(
        user.degree_level is not None and user.field_id is not None and user.target_countries
    )
