"""Admin paneldan bot orqali userlarga xabar yuborish.

Tartib: admin xabarni yozadi -> qoralama saqlanadi va bot adminlariga SINOV
sifatida yuboriladi -> admin ko'rib chiqib "Hammaga yuborish" ni bosadi.
Sinovsiz ommaviy yuborishning iloji yo'q: xato HTML yoki noto'g'ri havola
minglab odamga ketib qolmasin.

Ommaviy yuborish veb-jarayon ichida fonda ketadi (sekundiga ~25 xabar,
Telegram chegarasidan past). Hisoblagichlar bazaga yozib boriladi, admin
sahifasi ularni ko'rsatadi. Jarayon qayta ishga tushsa, yuborish davom
ETMAYDI — yozuv "to'xtatilgan" bo'lib qoladi (`mark_interrupted`).

Botni bloklagan user `is_blocked` deb BELGILANMAYDI: bu bayroq hisobni
cheklash uchun ham ishlatiladi, Mini App orqali kelib botga /start bosmagan
odamga ham Telegram xuddi shunday 403 qaytaradi.
"""

import asyncio
import logging
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Broadcast, User
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

MESSAGES_PER_SECOND = 25
_SEND_INTERVAL = 1 / MESSAGES_PER_SECOND
# Hisoblagichlar bazaga har shuncha xabardan keyin yoziladi.
PROGRESS_EVERY = 25
MAX_IMAGE_BYTES = 5 * 1024 * 1024
CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096

STATUS_DRAFT = "draft"
STATUS_SENDING = "sending"
STATUS_DONE = "done"
STATUS_INTERRUPTED = "interrupted"

# Fondagi vazifalar: havolasi saqlanmasa, asyncio ularni yig'ib tashlashi mumkin.
_tasks: set[asyncio.Task] = set()


def _recipients(audience: str):
    stmt = select(User).where(User.is_blocked.is_(False))
    if audience in ("uz", "ru", "en"):
        stmt = stmt.where(User.ui_language == audience)
    return stmt


async def count_recipients(session: AsyncSession, audience: str) -> int:
    stmt = _recipients(audience).with_only_columns(func.count())
    return (await session.execute(stmt)).scalar_one()


def validate(text: str, has_image: bool, button_text: str, button_kind: str, button_url: str):
    """Xato matni yoki None."""
    if not text.strip():
        return "Xabar matni bo'sh."
    limit = CAPTION_LIMIT if has_image else TEXT_LIMIT
    if len(text) > limit:
        return (
            f"Matn juda uzun: {len(text)} belgi (rasm bilan {CAPTION_LIMIT}, rasmsiz {TEXT_LIMIT})."
        )
    if button_text and button_kind == "url" and not button_url.startswith(("https://", "http://")):
        return "Tugma havolasi https:// bilan boshlanishi kerak."
    if button_url and not button_text:
        return "Tugma matnini yozing (yoki havolani o'chiring)."
    return None


def build_markup(broadcast: Broadcast) -> InlineKeyboardMarkup | None:
    if not broadcast.button_text:
        return None
    if broadcast.button_kind == "url" and broadcast.button_url:
        button = InlineKeyboardButton(text=broadcast.button_text, url=broadcast.button_url)
    else:
        url = broadcast.button_url or settings.webapp_url
        button = InlineKeyboardButton(text=broadcast.button_text, web_app=WebAppInfo(url=url))
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def new_bot() -> Bot:
    return Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def send_one(bot: Bot, chat_id: int, broadcast: Broadcast, photo) -> str | None:
    """Bitta xabar. Rasm birinchi marta fayl bo'lib ketadi; qaytgan `file_id`
    keyingilarida qayta ishlatiladi (rasm har safar qayta yuklanmaydi)."""
    markup = build_markup(broadcast)
    if photo is None:
        await bot.send_message(chat_id, broadcast.text, reply_markup=markup)
        return None
    message = await bot.send_photo(chat_id, photo, caption=broadcast.text, reply_markup=markup)
    return message.photo[-1].file_id if message.photo else None


def first_photo(broadcast: Broadcast):
    if not broadcast.image_data:
        return None
    ext = (broadcast.image_type or "image/jpeg").split("/")[-1]
    return BufferedInputFile(broadcast.image_data, filename=f"broadcast.{ext}")


async def send_test(broadcast: Broadcast, chat_ids: list[int]) -> list[str]:
    """Sinov xabari. Qaytadi: xatolar ro'yxati (bo'sh — hammasi yetdi)."""
    errors: list[str] = []
    bot = new_bot()
    try:
        photo = first_photo(broadcast)
        for chat_id in chat_ids:
            try:
                file_id = await send_one(bot, chat_id, broadcast, photo)
                if file_id:
                    photo = file_id
            except Exception as exc:  # noqa: BLE001 — xato adminga ko'rsatiladi
                errors.append(f"{chat_id}: {exc}")
    finally:
        await bot.session.close()
    return errors


async def _save_progress(broadcast_id: int, **values) -> None:
    async with async_session_factory() as session:
        await session.execute(
            update(Broadcast).where(Broadcast.id == broadcast_id).values(**values)
        )
        await session.commit()


async def run_broadcast(broadcast_id: int) -> None:
    """Fondagi ommaviy yuborish (o'z sessiyasi va boti bilan)."""
    async with async_session_factory() as session:
        broadcast = await session.get(Broadcast, broadcast_id)
        if broadcast is None:
            return
        await session.refresh(broadcast, attribute_names=["image_data"])
        chat_ids = list(
            (
                await session.execute(
                    _recipients(broadcast.audience)
                    .with_only_columns(User.telegram_id)
                    .order_by(User.id)
                )
            )
            .scalars()
            .all()
        )
        session.expunge(broadcast)

    sent = failed = blocked = 0
    await _save_progress(broadcast_id, total=len(chat_ids))
    bot = new_bot()
    photo = first_photo(broadcast)
    try:
        for index, chat_id in enumerate(chat_ids, start=1):
            try:
                try:
                    file_id = await send_one(bot, chat_id, broadcast, photo)
                except TelegramRetryAfter as exc:
                    await asyncio.sleep(exc.retry_after)
                    file_id = await send_one(bot, chat_id, broadcast, photo)
                if file_id:
                    photo = file_id
                sent += 1
            except TelegramForbiddenError:
                blocked += 1
            except Exception:  # noqa: BLE001 — bitta xato ommaviy yuborishni to'xtatmasin
                failed += 1
                logger.warning("Xabar yuborilmadi: broadcast=%s chat=%s", broadcast_id, chat_id)
            if index % PROGRESS_EVERY == 0:
                await _save_progress(broadcast_id, sent=sent, failed=failed, blocked=blocked)
            await asyncio.sleep(_SEND_INTERVAL)
        await _save_progress(
            broadcast_id,
            sent=sent,
            failed=failed,
            blocked=blocked,
            status=STATUS_DONE,
            finished_at=datetime.now(UTC),
        )
    except asyncio.CancelledError:
        await _save_progress(
            broadcast_id, sent=sent, failed=failed, blocked=blocked, status=STATUS_INTERRUPTED
        )
        raise
    except Exception:
        logger.exception("Ommaviy yuborish to'xtadi: broadcast=%s", broadcast_id)
        await _save_progress(
            broadcast_id, sent=sent, failed=failed, blocked=blocked, status=STATUS_INTERRUPTED
        )
    finally:
        await bot.session.close()


def start(broadcast_id: int) -> None:
    task = asyncio.create_task(run_broadcast(broadcast_id), name=f"broadcast-{broadcast_id}")
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def mark_interrupted() -> None:
    """Jarayon qayta ishga tushganda: yarmida qolgan yuborishlar to'xtatilgan."""
    try:
        async with async_session_factory() as session:
            await session.execute(
                update(Broadcast)
                .where(Broadcast.status == STATUS_SENDING)
                .values(status=STATUS_INTERRUPTED)
            )
            await session.commit()
    except Exception:
        logger.exception("Yuborish holatlarini yangilab bo'lmadi")
