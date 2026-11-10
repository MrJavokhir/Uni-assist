"""Admission Kit qo'llanmalari: PDF saqlash, egalik va yetkazish.

Qulf mantig'i bitta joyda turadi, chunki u ikki tomondan so'raladi —
ilova ro'yxatni ko'rsatishda, yetkazish endpointi esa faylni berishdan
oldin. Ikki joyda alohida yozilsa, biri o'zgarib ikkinchisi qolib ketardi
va pul to'lamagan odam faylni olib qo'yishi mumkin edi.

Egalik yozuvi — `ServiceRequest`. Alohida "purchases" jadvali qilinmadi:
xizmat sotib olinganda pul `payment_service.charge_service()` orqali
yechiladi va shu bitta yozuv "to'landi" degan ma'noni beradi. Ikkita
jadval bo'lsa, ular bir-biriga mos kelmay qolishi mumkin edi.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from html import escape

from aiogram import Bot
from aiogram.types import BufferedInputFile
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, undefer

from app.db.models import (
    AdmissionService,
    BalanceTransaction,
    ServiceFile,
    ServiceKind,
    ServiceRequest,
    TransactionKind,
    User,
)

logger = logging.getLogger(__name__)

# Telegram `sendDocument` 50 MB'gacha ko'taradi. 20 MB'da to'xtaymiz:
# qo'llanma uchun bu ko'p bilan yetarli, baza satri esa haddan tashqari
# kattalashib ketmaydi.
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_ICON_BYTES = 1024 * 1024
ALLOWED_ICON_TYPES = {"image/jpeg", "image/png", "image/webp"}

# PDF faylning boshi. Kengaytmaga ishonmaymiz: .pdf deb nomlangan word
# fayli yuklansa, foydalanuvchi ochib ko'rgandagina bilardi.
PDF_MAGIC = b"%PDF-"


class FileRejected(Exception):
    """Yuklangan fayl qabul qilinmadi (tur yoki o'lcham)."""


def _clean_filename(name: str) -> str:
    """Faylning faqat nomini qoldiradi.

    Brauzerlar ba'zan faqat nomni emas, to'liq yo'lni yuboradi; bundan
    tashqari nom Telegram'ga sarlavha sifatida ketadi — papka belgilari
    kerak emas.
    """
    base = name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    base = "".join(ch for ch in base if ch.isprintable()) or "qollanma.pdf"
    if not base.lower().endswith(".pdf"):
        base = f"{base}.pdf"
    return base[:200]


async def save_file(
    session: AsyncSession, service: AdmissionService, filename: str, data: bytes
) -> ServiceFile:
    """PDF'ni xizmatga biriktiradi (bori bo'lsa — o'rniga yozadi)."""
    if not data:
        raise FileRejected("Fayl bo'sh.")
    if len(data) > MAX_PDF_BYTES:
        raise FileRejected(
            f"Fayl juda katta: {len(data) / 1024 / 1024:.1f} MB. "
            f"Chegara — {MAX_PDF_BYTES // 1024 // 1024} MB."
        )
    if not data.startswith(PDF_MAGIC):
        raise FileRejected("Faqat PDF qabul qilinadi (fayl PDF formatida emas).")

    row = await _row(session, service.id, with_data=False)
    if row is None:
        row = ServiceFile(service_id=service.id)
        session.add(row)

    row.filename = _clean_filename(filename)
    row.content_type = "application/pdf"
    row.size_bytes = len(data)
    row.data = data
    # Fayl almashdi — Telegram'dagi eski nusxaning id'si endi yaramaydi,
    # aks holda sotib olgan odam eski PDF'ni olardi.
    row.telegram_file_id = None
    await session.flush()
    return row


async def delete_file(session: AsyncSession, service: AdmissionService) -> bool:
    row = await _row(session, service.id, with_data=False)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def _row(session: AsyncSession, service_id: int, *, with_data: bool) -> ServiceFile | None:
    stmt = select(ServiceFile).where(ServiceFile.service_id == service_id)
    if with_data:
        # `data` modelda deferred — baytlar faqat shu yerda ataylab so'raladi.
        stmt = stmt.options(undefer(ServiceFile.data))
    return (await session.execute(stmt)).scalar_one_or_none()


async def file_meta(session: AsyncSession, service_id: int) -> ServiceFile | None:
    """Fayl ma'lumoti baytlarsiz: nomi, o'lchami, yuklangan vaqti."""
    return await _row(session, service_id, with_data=False)


async def owned_service_ids(session: AsyncSession, user: User) -> set[int]:
    """Foydalanuvchi sotib olgan (yoki so'rov yuborgan) xizmatlar."""
    stmt = select(ServiceRequest.service_id).where(ServiceRequest.user_id == user.id)
    return set((await session.execute(stmt)).scalars().all())


async def owns(session: AsyncSession, user: User, service_id: int) -> bool:
    stmt = select(ServiceRequest.id).where(
        ServiceRequest.user_id == user.id, ServiceRequest.service_id == service_id
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


# Xizmat qanday olingan.
OBTAINED_PAID = "paid"
OBTAINED_INVITES = "invites"
OBTAINED_FREE = "free"
OBTAINED_GIFT = "gift"


@dataclass(frozen=True)
class ObtainedRow:
    request: ServiceRequest
    how: str
    # Haqiqatda yechilgan summa; pul yechilmagan bo'lsa None.
    paid: Decimal | None


def _paid_amount():
    """Shu olish uchun balansdan yechilgan summa.

    Xizmatning hozirgi narxiga qaralmaydi: narx keyin qo'yilgan yoki
    o'zgartirilgan bo'lishi mumkin. Haqiqiy yechim balans tarixida turadi.
    """
    return (
        select(func.sum(-BalanceTransaction.amount))
        .where(
            BalanceTransaction.user_id == ServiceRequest.user_id,
            BalanceTransaction.service_id == ServiceRequest.service_id,
            BalanceTransaction.kind == TransactionKind.SERVICE,
        )
        .correlate(ServiceRequest)
        .scalar_subquery()
    )


def _how_obtained():
    return case(
        (ServiceRequest.unlocked_by_invites.is_(True), OBTAINED_INVITES),
        (ServiceRequest.gift_discount.is_not(None), OBTAINED_GIFT),
        (_paid_amount().is_not(None), OBTAINED_PAID),
        else_=OBTAINED_FREE,
    )


async def obtained_counts(session: AsyncSession) -> dict[int, dict[str, int]]:
    """Har xizmat necha marta va qanday olingani: {service_id: {how: soni}}."""
    rows = select(ServiceRequest.service_id, _how_obtained().label("how")).subquery()
    stmt = select(rows.c.service_id, rows.c.how, func.count()).group_by(
        rows.c.service_id, rows.c.how
    )
    counts: dict[int, dict[str, int]] = {}
    for service_id, how, count in await session.execute(stmt):
        counts.setdefault(service_id, {})[how] = count
    return counts


async def obtained_rows(
    session: AsyncSession,
    *,
    how: str | None = None,
    kind: ServiceKind | None = None,
    limit: int | None = None,
) -> list[ObtainedRow]:
    """Olingan xizmatlar, eng yangisi birinchi."""
    how_obtained = _how_obtained()
    stmt = (
        select(ServiceRequest, how_obtained, _paid_amount())
        .join(ServiceRequest.service)
        .options(selectinload(ServiceRequest.service), selectinload(ServiceRequest.user))
        .order_by(ServiceRequest.id.desc())
        .limit(limit)
    )
    if how is not None:
        stmt = stmt.where(how_obtained == how)
    if kind is not None:
        stmt = stmt.where(AdmissionService.kind == kind)
    rows = await session.execute(stmt)
    return [ObtainedRow(request, row_how, paid) for request, row_how, paid in rows]


async def deliver_file(
    session: AsyncSession, bot: Bot, user: User, service: AdmissionService
) -> ServiceFile | None:
    """Sotib olingan PDF'ni bot suhbatiga yuboradi.

    Egalik BU YERDA tekshirilmaydi — chaqiruvchi tekshiradi (`owns`), chunki
    u "sotib olinmagan" holatda foydalanuvchiga boshqacha javob qaytaradi.

    Fayl bir marta Telegram'ga yuklanadi, keyin `file_id` bilan yuboriladi:
    har bosishda 10 MB'ni qayta jo'natish ham sekin, ham keraksiz.
    """
    row = await _row(session, service.id, with_data=True)
    if row is None:
        return None

    # HTML rejimida yuboriladi, sarlavha esa adminkadan kelgan erkin matn —
    # ichida "&" yoki "<" bo'lsa Telegram butun xabarni rad etardi.
    caption = f"📘 <b>{escape(service.title_uz)}</b>\n\n{escape(row.filename)}"

    if row.telegram_file_id:
        try:
            await bot.send_document(
                user.telegram_id, row.telegram_file_id, caption=caption, parse_mode="HTML"
            )
            return row
        except Exception:  # noqa: BLE001 — sababi muhim emas, qayta yuklaymiz
            # Keshlangan id yaramay qolgan (fayl Telegram'da o'chgan yoki
            # bot tokeni almashgan) — baytlardan qayta yuklaymiz.
            logger.warning("Keshlangan file_id ishlamadi, qayta yuklanadi: xizmat=%s", service.id)
            row.telegram_file_id = None

    sent = await bot.send_document(
        user.telegram_id,
        BufferedInputFile(row.data, filename=row.filename),
        caption=caption,
        parse_mode="HTML",
    )
    if sent.document:
        row.telegram_file_id = sent.document.file_id
        await session.flush()
    return row


def save_icon(service: AdmissionService, content_type: str | None, data: bytes) -> None:
    """Xizmat ikonkasini yozadi. Noto'g'ri fayl `FileRejected` beradi."""
    kind = (content_type or "").split(";")[0].strip().lower()
    if kind not in ALLOWED_ICON_TYPES:
        raise FileRejected("Ikonka JPG, PNG yoki WebP formatida bo'lishi kerak.")
    if not data:
        raise FileRejected("Fayl bo'sh.")
    if len(data) > MAX_ICON_BYTES:
        raise FileRejected(f"Ikonka juda katta. Chegara — {MAX_ICON_BYTES // 1024 // 1024} MB.")
    service.icon_data = data
    service.icon_type = kind
    service.icon_version = (service.icon_version or 0) + 1


def delete_icon(service: AdmissionService) -> None:
    service.icon_data = None
    service.icon_type = None
    service.icon_version = 0


def icon_url(service: AdmissionService) -> str | None:
    """Mini App va admin uchun ikonka manzili; `v` kesh eskirmasligi uchun."""
    if service.icon_version:
        return f"/api/webapp/images/service/{service.id}?v={service.icon_version}"
    return service.image_url
