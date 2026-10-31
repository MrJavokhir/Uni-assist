"""Hukumat grantlari bo'yicha deadline eslatmasi: ariza muddati tugashiga 30 kun qolganda.

Dastur eslatmalaridan (`reminder_service`) farqi: grant saqlanmaydi, shuning
uchun eslatma eslatmalari yoqilgan HAMMA foydalanuvchiga ketadi. Faqat bitta
cheklov — daraja: grant boshqa darajaga mo'ljallangan bo'lsa (magistr
profiliga "MEXT Undergraduate"), u odamga yuborilmaydi.

Bir kunda bir nechta grant to'g'ri kelsa — bitta jamlangan xabar.
Dublikat nazorati `scholarship_notification_logs` jadvalida.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    DeadlineType,
    Scholarship,
    ScholarshipNotificationLog,
    User,
)
from app.i18n import t
from app.services.reminder_service import MESSAGES_PER_SECOND, _webapp
from app.services.timezone_utils import TASHKENT_TZ

logger = logging.getLogger(__name__)

# Muddat tugashiga shuncha kun qolganda eslatiladi.
REMIND_DAYS_BEFORE = 30
# Scheduler bir-ikki kun ishlamay qolsa ham eslatma yo'qolmasin: 28–30 kun
# oralig'ida hali yuborilmagan bo'lsa yuboriladi. Undan kechroq — endi
# "30 kun" xabari emas, yubormaymiz.
CATCH_UP_DAYS = 2


@dataclass
class GrantReminder:
    scholarship: Scholarship
    deadline_date: date
    days_left: int


@dataclass
class GrantScanResult:
    due: list[GrantReminder] = field(default_factory=list)
    sent_users: int = 0
    blocked_users: int = 0


def due_reminders(scholarship: Scholarship, today: date) -> list[GrantReminder]:
    """Grantning bugun eslatiladigan muddatlari (bosqichli bo'lsa — har biri)."""
    result = []
    for deadline in scholarship.deadlines:
        if deadline.type != DeadlineType.APPLICATION_CLOSE:
            continue
        close = deadline.date_utc.astimezone(TASHKENT_TZ).date()
        days_left = (close - today).days
        if REMIND_DAYS_BEFORE - CATCH_UP_DAYS <= days_left <= REMIND_DAYS_BEFORE:
            result.append(GrantReminder(scholarship, close, days_left))
    return result


def fits_user(scholarship: Scholarship, user: User) -> bool:
    """Grant foydalanuvchi darajasiga mosmi (daraja noma'lum bo'lsa — mos)."""
    levels = scholarship.degree_levels or []
    return not levels or user.degree_level is None or user.degree_level.value in levels


def build_message(reminders: list[GrantReminder], lang: str) -> tuple[str, InlineKeyboardMarkup]:
    lines = [] if len(reminders) == 1 else [t("notif.scholarship_digest_header", lang), ""]
    rows: list[list[InlineKeyboardButton]] = []
    for item in reminders:
        lines.append(
            t(
                "notif.scholarship_30d",
                lang,
                name=item.scholarship.name,
                days=item.days_left,
                date=item.deadline_date.isoformat(),
            )
        )
        lines.append("")
        row = []
        app_link = _webapp(f"grant_{item.scholarship.id}")
        if app_link is not None:
            row.append(InlineKeyboardButton(text=t("notif.btn_open", lang), web_app=app_link))
        if item.scholarship.source_url:
            row.append(
                InlineKeyboardButton(
                    text=t("notif.btn_site", lang), url=item.scholarship.source_url
                )
            )
        if row:
            rows.append(row)
    settings_link = _webapp("profile")
    if settings_link is not None:
        rows.append(
            [InlineKeyboardButton(text=t("notif.btn_settings", lang), web_app=settings_link)]
        )
    return "\n".join(lines).strip(), InlineKeyboardMarkup(inline_keyboard=rows)


async def _send(bot: Bot, user: User, text: str, markup: InlineKeyboardMarkup) -> bool:
    try:
        await bot.send_message(user.telegram_id, text, reply_markup=markup)
    except TelegramForbiddenError:
        user.is_blocked = True
        return False
    except TelegramRetryAfter as exc:
        await asyncio.sleep(exc.retry_after)
        try:
            await bot.send_message(user.telegram_id, text, reply_markup=markup)
        except Exception:
            logger.exception("Grant eslatmasi qayta urinishda ham ketmadi: user_id=%s", user.id)
            return False
    except Exception:
        logger.exception("Grant eslatmasi yuborilmadi: user_id=%s", user.id)
        return False
    return True


async def run_scholarship_reminder_scan(
    bot: Bot | None,
    session: AsyncSession,
    *,
    today: date | None = None,
    dry_run: bool = False,
) -> GrantScanResult:
    """Bugun 30 kuni qolgan grantlarni topib, foydalanuvchilarga yuboradi."""
    today = today or datetime.now(TASHKENT_TZ).date()
    result = GrantScanResult()

    scholarships = (
        (await session.execute(select(Scholarship).options(selectinload(Scholarship.deadlines))))
        .scalars()
        .all()
    )
    for scholarship in scholarships:
        result.due.extend(due_reminders(scholarship, today))
    if not result.due:
        return result

    users = (
        (
            await session.execute(
                select(User).where(User.is_blocked.is_(False), User.notifications_enabled.is_(True))
            )
        )
        .scalars()
        .all()
    )
    sent = {
        (row.user_id, row.scholarship_id, row.deadline_date)
        for row in (
            await session.execute(
                select(
                    ScholarshipNotificationLog.user_id,
                    ScholarshipNotificationLog.scholarship_id,
                    ScholarshipNotificationLog.deadline_date,
                ).where(
                    ScholarshipNotificationLog.scholarship_id.in_(
                        {item.scholarship.id for item in result.due}
                    )
                )
            )
        ).all()
    }

    for user in users:
        items = [
            item
            for item in result.due
            if fits_user(item.scholarship, user)
            and (user.id, item.scholarship.id, item.deadline_date) not in sent
        ]
        if not items:
            continue
        if dry_run:
            result.sent_users += 1
            continue

        assert bot is not None, "dry_run bo'lmaganda bot kerak"
        text, markup = build_message(items, user.ui_language.value)
        if not await _send(bot, user, text, markup):
            if user.is_blocked:
                result.blocked_users += 1
            continue
        session.add_all(
            ScholarshipNotificationLog(
                user_id=user.id,
                scholarship_id=item.scholarship.id,
                deadline_date=item.deadline_date,
            )
            for item in items
        )
        # Har xabardan keyin saqlanadi: jarayon o'rtada uzilsa, yuborilganlari
        # qayta ketmaydi.
        await session.commit()
        result.sent_users += 1
        await asyncio.sleep(1 / MESSAGES_PER_SECOND)

    await session.commit()
    return result
