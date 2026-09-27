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
from html import escape

from aiogram import Bot
from aiogram.types import BufferedInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.db.models import AdmissionService, ServiceFile, ServiceRequest, User

logger = logging.getLogger(__name__)

# Telegram `sendDocument` 50 MB'gacha ko'taradi. 20 MB'da to'xtaymiz:
# qo'llanma uchun bu ko'p bilan yetarli, baza satri esa haddan tashqari
# kattalashib ketmaydi.
MAX_PDF_BYTES = 20 * 1024 * 1024

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
