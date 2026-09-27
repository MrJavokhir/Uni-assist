"""Uchrashuv vaqtlari: bo'sh oynalar va ularni band qilish.

Vaqtlarni ADMIN kiritadi, foydalanuvchi faqat bo'shlaridan birini
tanlaydi. Kalendar bilan integratsiya yo'q: mentorning haqiqiy bandligini
bilmasdan avtomatik vaqt taklif qilish xato uchrashuvlarga olib kelardi.

Band qilish shu modulda va FAQAT shu yerda bajariladi. Sabab: ikki odam
bir vaqtda bitta oynani tanlashi mumkin. "Avval o'qib, keyin yozish"
usuli bunday holatda ikkalasiga ham ruxsat berardi, shuning uchun band
qilish bitta shartli UPDATE bilan qilinadi va nechta qator o'zgargani
tekshiriladi.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ServiceSlot
from app.services.timezone_utils import to_tashkent

logger = logging.getLogger(__name__)

# Ro'yxat cheksiz uzun bo'lib ketmasligi uchun: ilovada bir ekranga
# sig'adigan miqdor yetarli, qolgani pastga cho'zilib ketardi.
MAX_SLOTS_SHOWN = 40

# Hafta kunlari — sana yonida turadi. Oy nomlarini uch tilda yuritmaslik
# uchun sana raqamlar bilan (05.10.2026) ko'rsatiladi: u har qanday tilda
# bir xil o'qiladi, hafta kuni esa tanlashda eng muhim ma'lumot.
_WEEKDAYS = {
    "uz": [
        "dushanba",
        "seshanba",
        "chorshanba",
        "payshanba",
        "juma",
        "shanba",
        "yakshanba",
    ],
    "ru": [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ],
    "en": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
}


class SlotTaken(Exception):
    """Oynani boshqa birov band qilib ulgurdi."""


def _now() -> datetime:
    return datetime.now(UTC)


def labels(slot: ServiceSlot, lang: str) -> tuple[str, str]:
    """(sana, vaqt) — Toshkent vaqtida, foydalanuvchi tilida."""
    local = to_tashkent(slot.starts_at)
    weekday = _WEEKDAYS.get(lang, _WEEKDAYS["uz"])[local.weekday()]
    return f"{local:%d.%m.%Y}, {weekday}", f"{local:%H:%M}"


def _free_condition(service_id: int):
    return (
        ServiceSlot.service_id == service_id,
        ServiceSlot.request_id.is_(None),
        # O'tib ketgan vaqt taklif qilinmaydi.
        ServiceSlot.starts_at > _now(),
    )


async def free_slots(session: AsyncSession, service_id: int) -> list[ServiceSlot]:
    stmt = (
        select(ServiceSlot)
        .where(*_free_condition(service_id))
        .order_by(ServiceSlot.starts_at)
        .limit(MAX_SLOTS_SHOWN)
    )
    return list((await session.execute(stmt)).scalars().all())


async def free_counts(session: AsyncSession) -> dict[int, int]:
    """Har bir xizmat uchun nechta bo'sh oyna bor.

    Xizmatlar ro'yxati uchun: har qator uchun alohida so'rov yuborish
    o'rniga hammasi birdan sanaladi.
    """
    stmt = (
        select(ServiceSlot.service_id, func.count())
        .where(ServiceSlot.request_id.is_(None), ServiceSlot.starts_at > _now())
        .group_by(ServiceSlot.service_id)
    )
    return dict((await session.execute(stmt)).all())


async def claim(session: AsyncSession, slot_id: int, service_id: int, request_id: int) -> None:
    """Oynani band qiladi. Band bo'lib ulgurgan bo'lsa — `SlotTaken`.

    Bitta shartli UPDATE: ikki odam bir vaqtda bosganda faqat bittasi
    qator o'zgartira oladi. Chaqiruvchi xatoni ushlab, tranzaksiyani
    bekor qiladi — demak pul ham yechilmaydi.
    """
    stmt = (
        update(ServiceSlot)
        .where(
            ServiceSlot.id == slot_id,
            ServiceSlot.service_id == service_id,
            ServiceSlot.request_id.is_(None),
            ServiceSlot.starts_at > _now(),
        )
        .values(request_id=request_id)
    )
    result = await session.execute(stmt)
    if result.rowcount != 1:
        logger.info("Oyna band bo'lib ulgurdi: slot=%s, xizmat=%s", slot_id, service_id)
        raise SlotTaken

    # Bazada yozildi, lekin sessiyada ALLAQACHON o'qilgan nusxa eski
    # holatida qolgan bo'lishi mumkin. Keyin o'sha nusxaga qarab "bo'sh"
    # degan xulosa chiqarilsa, band vaqt bo'sh deb ko'rinardi — shuning
    # uchun majburan qayta o'qiymiz.
    cached = await session.get(ServiceSlot, slot_id)
    if cached is not None:
        await session.refresh(cached)


async def add_slot(
    session: AsyncSession,
    service_id: int,
    starts_at: datetime,
    duration_minutes: int = 60,
    note: str | None = None,
) -> ServiceSlot:
    slot = ServiceSlot(
        service_id=service_id,
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        note=note or None,
    )
    session.add(slot)
    await session.flush()
    return slot


async def delete_slot(session: AsyncSession, slot_id: int) -> bool:
    """Bo'sh oynani o'chiradi.

    Band qilingani o'chirilmaydi: odam pul to'lagan va o'sha vaqtga
    yozilgan. Uchrashuvni bekor qilish kerak bo'lsa, so'rovning holati
    o'zgartiriladi va odam bilan gaplashiladi.
    """
    # Shartli DELETE: "avval o'qib, keyin o'chirish" oralig'ida kimdir
    # band qilib ulgurishi mumkin edi. Bitta so'rovda bajarilsa, bunday
    # oraliq umuman qolmaydi.
    result = await session.execute(
        delete(ServiceSlot)
        .where(ServiceSlot.id == slot_id, ServiceSlot.request_id.is_(None))
        .execution_options(synchronize_session="fetch")
    )
    return result.rowcount == 1
