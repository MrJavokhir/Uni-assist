"""Saqlangan dasturlar bo'yicha deadline eslatmalari.

Eslatma jadvali: deadline'gacha 60/30/14/7/3/1 kun qolganda. Har bir
(saved_program, deadline, kun) kombinatsiyasi uchun faqat bitta marta
yuboriladi — buni Redis'dagi dedup kalit orqali nazorat qilamiz, shunda
bot qayta ishga tushirilganda eslatmalar takrorlanmaydi yoki yo'qolmaydi
(holat DB + Redis'da, jarayon xotirasida emas).
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Deadline, Program, SavedProgram
from app.i18n import t
from app.services.timezone_utils import format_tashkent

logger = logging.getLogger(__name__)

REMINDER_THRESHOLDS_DAYS: tuple[int, ...] = (60, 30, 14, 7, 3, 1)

# Redis'da eslatma "yuborildi" belgisi qancha vaqt saqlanishi (sekund) —
# eng uzoq deadline'dan ham oshiqcha, shunchaki kalitlar abadiy to'planmasin uchun.
_DEDUP_TTL_SECONDS = 400 * 24 * 3600


@dataclass
class DueReminder:
    saved_program: SavedProgram
    deadline: Deadline
    days_left: int


def _dedup_key(saved_program_id: int, deadline_id: int, days_left: int) -> str:
    return f"reminder_sent:{saved_program_id}:{deadline_id}:{days_left}"


async def find_due_reminders(session: AsyncSession, *, now: datetime | None = None) -> list[DueReminder]:
    now = now or datetime.now(UTC)
    today = now.date()

    stmt = (
        select(SavedProgram)
        .where(SavedProgram.reminders_active.is_(True))
        .options(
            selectinload(SavedProgram.program).selectinload(Program.deadlines),
            selectinload(SavedProgram.program).selectinload(Program.university),
            selectinload(SavedProgram.user),
        )
    )
    saved_programs = (await session.execute(stmt)).scalars().all()

    due: list[DueReminder] = []
    for saved in saved_programs:
        for deadline in saved.program.deadlines:
            days_left = (deadline.date_utc.date() - today).days
            if days_left in REMINDER_THRESHOLDS_DAYS:
                due.append(DueReminder(saved_program=saved, deadline=deadline, days_left=days_left))
    return due


async def is_already_sent(redis: Redis, reminder: DueReminder) -> bool:
    key = _dedup_key(reminder.saved_program.id, reminder.deadline.id, reminder.days_left)
    return bool(await redis.exists(key))


async def mark_sent(redis: Redis, reminder: DueReminder) -> None:
    key = _dedup_key(reminder.saved_program.id, reminder.deadline.id, reminder.days_left)
    await redis.set(key, "1", ex=_DEDUP_TTL_SECONDS)


def _reminder_keyboard(saved_program_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("reminder.done_button", lang), callback_data=f"remind_done:{saved_program_id}"
                ),
                InlineKeyboardButton(
                    text=t("reminder.dismiss_button", lang), callback_data=f"remind_dismiss:{saved_program_id}"
                ),
            ]
        ]
    )


async def send_reminder(bot: Bot, reminder: DueReminder) -> None:
    user = reminder.saved_program.user
    lang = user.ui_language.value
    program = reminder.saved_program.program

    text = t(
        "reminder.title",
        lang,
        program=program.name,
        university=program.university.name,
        deadline_type=t(f"deadline.type.{reminder.deadline.type.value}", lang),
        days=reminder.days_left,
        date=format_tashkent(reminder.deadline.date_utc),
    )
    await bot.send_message(
        user.telegram_id,
        text,
        reply_markup=_reminder_keyboard(reminder.saved_program.id, lang),
    )


async def run_reminder_scan(bot: Bot, session: AsyncSession, redis: Redis) -> int:
    """Barcha yaqinlashayotgan deadline'larni topib, yuborilmagan eslatmalarni yuboradi.

    Qaytadi: shu ishga tushirishda yuborilgan eslatmalar soni.
    """
    due_reminders = await find_due_reminders(session)
    sent_count = 0

    for reminder in due_reminders:
        if await is_already_sent(redis, reminder):
            continue
        try:
            await send_reminder(bot, reminder)
        except Exception:
            logger.exception(
                "Eslatma yuborishda xatolik: saved_program_id=%s", reminder.saved_program.id
            )
            continue
        await mark_sent(redis, reminder)
        sent_count += 1

    return sent_count
