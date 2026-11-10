"""Haftalik "sizga mos dastur topildi" xabari.

Har seshanba (eslatmalar bilan bir vaqtda, Toshkent vaqti 10:00) filtri
to'liq va bildirishnomalari yoqilgan har bir foydalanuvchiga BITTA xabar:
unga hali tavsiya qilinmagan va u saqlamagan eng mos dastur. Xabar
ulashish xabariga o'xshaydi — karta rasmi, qisqa matn va "Dastur bilan
tanishish" tugmasi (app/services/share_card.py).

Tanlash tartibi: avval to'liq mos (yashil), keyin qisman mos (sariq);
bir xil darajada — katalogga eng oxirgi qo'shilgani. Muddati o'tgan
(qizil) dasturlar tavsiya qilinmaydi. Mos dastur qolmagan bo'lsa, o'sha
hafta xabar ketmaydi.

Dublikat nazorati `match_notifications` jadvalida (unique user+program).
Har foydalanuvchidan keyin commit qilinadi: jarayon yarmida to'xtasa ham,
qayta ishga tushganda allaqachon yuborilganlarga takror ketmaydi.

"BUGUN" PARAMETR: testlar kalendarga bog'liq emas.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import MatchNotification, Program, User
from app.i18n import t
from app.services import share_card
from app.services.event_service import filter_is_complete
from app.services.matching_service import MatchLevel, find_matches
from app.services.reminder_service import _SEND_INTERVAL, _webapp
from app.services.timezone_utils import TASHKENT_TZ
from app.services.user_service import _PROFILE_RELATIONSHIPS

logger = logging.getLogger(__name__)

# Haftaning qaysi kuni yuboriladi (0 = dushanba, 1 = seshanba).
MATCH_WEEKDAY = 1

_LEVEL_ORDER = {MatchLevel.GREEN: 0, MatchLevel.YELLOW: 1}


@dataclass
class MatchScanResult:
    eligible_users: int = 0
    sent: int = 0
    no_match: int = 0
    blocked: int = 0


def is_match_day(today: date) -> bool:
    return today.weekday() == MATCH_WEEKDAY


async def eligible_users(session: AsyncSession) -> list[User]:
    """Bildirishnomalari yoqilgan, botni bloklamagan va filtri to'liq userlar."""
    users = (
        (
            await session.execute(
                select(User)
                .where(
                    User.notifications_enabled.is_(True),
                    User.is_blocked.is_(False),
                    User.degree_level.is_not(None),
                    User.field_id.is_not(None),
                )
                .options(*(selectinload(getattr(User, rel)) for rel in _PROFILE_RELATIONSHIPS))
                .order_by(User.id)
            )
        )
        .scalars()
        .all()
    )
    return [u for u in users if filter_is_complete(u)]


async def pick_program(session: AsyncSession, user: User) -> Program | None:
    """Userga hali tavsiya qilinmagan va u saqlamagan eng mos dastur."""
    already = set(
        (
            await session.execute(
                select(MatchNotification.program_id).where(MatchNotification.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    already |= {sp.program_id for sp in user.saved_programs}
    candidates = [
        r
        for r in await find_matches(session, user)
        if r.level in _LEVEL_ORDER and r.program.id not in already
    ]
    if not candidates:
        return None
    oldest = datetime.min.replace(tzinfo=UTC)
    candidates.sort(
        key=lambda r: (
            _LEVEL_ORDER[r.level],
            -(r.program.created_at or oldest).timestamp(),
            r.program.id,
        )
    )
    return candidates[0].program


def build_message(program: Program, lang: str, today: date) -> tuple[str, InlineKeyboardMarkup]:
    """Rasm izohi (HTML) va tugmalar."""
    caption = f"{t('match.found', lang)}\n\n{share_card.build_caption(program, lang, today)}"
    rows: list[list[InlineKeyboardButton]] = []
    app_link = _webapp(f"program_{program.id}")
    if app_link is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text=share_card.button_text(lang, share_card.KIND_PROGRAM), web_app=app_link
                )
            ]
        )
    settings_link = _webapp("profile")
    if settings_link is not None:
        rows.append(
            [InlineKeyboardButton(text=t("notif.btn_settings", lang), web_app=settings_link)]
        )
    return caption[: share_card.CAPTION_LIMIT], InlineKeyboardMarkup(inline_keyboard=rows)


async def _send(bot: Bot, user: User, program: Program, today: date) -> bool:
    """Karta rasmi bilan yuboradi; rasm yuborilmasa — oddiy matn bilan.

    403 (bot bloklangan) da `is_blocked` qo'yiladi va False qaytadi.
    """
    lang = user.ui_language.value
    caption, markup = build_message(program, lang, today)
    photo = share_card.program_image_url(program, lang, today)

    async def attempt() -> None:
        try:
            await bot.send_photo(
                user.telegram_id,
                photo,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
        except TelegramBadRequest:
            # Telegram rasmni yuklay olmadi (server band, rasm xatosi) —
            # xabar baribir yetib borsin.
            logger.warning("Mos dastur rasmi yuborilmadi, matn bilan: user_id=%s", user.id)
            await bot.send_message(
                user.telegram_id, caption, parse_mode=ParseMode.HTML, reply_markup=markup
            )

    try:
        await attempt()
    except TelegramForbiddenError:
        user.is_blocked = True
        logger.info("Bot bloklangan: user_id=%s", user.id)
        return False
    except TelegramRetryAfter as exc:
        await asyncio.sleep(exc.retry_after)
        try:
            await attempt()
        except Exception:
            logger.exception("Qayta urinish ham muvaffaqiyatsiz: user_id=%s", user.id)
            return False
    except Exception:
        logger.exception("Mos dastur xabarini yuborishda xatolik: user_id=%s", user.id)
        return False
    return True


async def run_match_scan(
    bot: Bot | None,
    session: AsyncSession,
    *,
    today: date | None = None,
    dry_run: bool = False,
) -> MatchScanResult:
    """Bir marta to'liq aylanish: har bir userga eng mos dastur yuboriladi."""
    today = today or datetime.now(TASHKENT_TZ).date()
    result = MatchScanResult()
    users = await eligible_users(session)
    result.eligible_users = len(users)

    for user in users:
        program = await pick_program(session, user)
        if program is None:
            result.no_match += 1
            continue
        if dry_run:
            result.sent += 1
            continue
        assert bot is not None, "dry_run bo'lmaganda bot kerak"
        if await _send(bot, user, program, today):
            session.add(MatchNotification(user_id=user.id, program_id=program.id))
            result.sent += 1
        elif user.is_blocked:
            result.blocked += 1
        await session.commit()
        await asyncio.sleep(_SEND_INTERVAL)
    return result
