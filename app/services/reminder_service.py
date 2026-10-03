"""Saqlangan dasturlar bo'yicha deadline eslatmalari.

QOIDA: bitta saqlangan dastur uchun ko'pi bilan IKKITA rejalashtirilgan xabar
(+ istisno holatda bitta "darhol" xabar). Ko'p dasturlarda aniq sana yo'q,
shuning uchun eslatmalar dasturdagi ma'lumot ANIQLIGIGA qarab tanlanadi:

  exact   — `deadlines` jadvalida ariza yopilish sanasi bor  -> 14 va 3 kun qolganda
  month   — faqat `programs.deadline_month` ma'lum           -> oldingi oy boshi va o'sha oy boshi
  unknown — hech narsa ma'lum emas                           -> saqlangandan 3 kun keyin bir marta

Aniqlik SAQLANMAYDI, hisoblab chiqariladi (`resolve_deadline`): aks holda u
`deadlines` jadvalidagi haqiqiy sanadan uzilib qolishi mumkin edi.

DUBLIKAT NAZORATI `notification_logs` jadvalida — unique (user, program, tur).
Ilgari bu Redis kalitlari bilan qilinardi; jadval afzal, chunki Redis
tozalansa xabarlar qaytadan ketmaydi va "bosildi" statistikasi yoziladi.

"BUGUN" HAR DOIM PARAMETR: butun mantiq sof funksiyalarda va sana tashqaridan
beriladi, shuning uchun testlar soat va kalendarga bog'liq emas.
"""

import asyncio
import logging
from calendar import monthrange
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import Enum

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import (
    Deadline,
    DeadlineType,
    NotificationLog,
    NotificationType,
    Program,
    SavedProgram,
    SavedProgramStatus,
    User,
)
from app.i18n import t
from app.services.timezone_utils import TASHKENT_TZ

logger = logging.getLogger(__name__)

# Kunlik jadval: eslatmalar shu soatda (Toshkent vaqti) yuboriladi.
DAILY_SEND_HOUR = 10

# Telegram ommaviy jo'natishda sekundiga ~30 xabarga ruxsat beradi. 25 —
# ataylab pastroq: 429 ga tez-tez tushib, retry bilan vaqt yo'qotgandan ko'ra
# bir oz sekin yuborgan ma'qul.
MESSAGES_PER_SECOND = 25
_SEND_INTERVAL = 1 / MESSAGES_PER_SECOND

# `unknown` dastur saqlangandan keyin necha kun o'tib eslatma yuboriladi.
UNKNOWN_CHECK_AFTER_DAYS = 3

# "Darhol" xabar chegaralari (kun).
IMMEDIATE_URGENT_DAYS = 3
IMMEDIATE_SOON_DAYS = 14

class DeadlinePrecision(str, Enum):
    EXACT = "exact"
    MONTH = "month"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class DeadlineInfo:
    """Dasturning deadline'i haqida bilganimiz."""

    precision: DeadlinePrecision
    exact_date: date | None = None
    month: int | None = None

@dataclass
class PlannedMessage:
    """Yuborilishi kerak bo'lgan bitta xabar."""

    saved: SavedProgram
    notif_type: NotificationType
    # Xabar qaysi kuni ketishi kerak edi. Scheduler bir kunni o'tkazib
    # yuborsa, bu sana o'tmishda qoladi va xabar baribir yuboriladi.
    due_on: date
    deadline_date: date | None = None
    month: int | None = None
    days_left: int | None = None

@dataclass
class ScanResult:
    """Bir marta ishga tushirish natijasi (hisobot va --dry-run uchun)."""

    planned: list[PlannedMessage] = field(default_factory=list)
    sent_users: int = 0
    sent_messages: int = 0
    blocked_users: int = 0

# ---------------------------------------------------------------- aniqlik --

def resolve_deadline(program: Program) -> DeadlineInfo:
    """Dasturdagi ma'lumotdan deadline aniqligini aniqlaydi.

    Aniq sana `deadlines` jadvalidan olinadi (ariza YOPILISHI turi). U sana
    UTC'da saqlanadi, lekin foydalanuvchi uchun Toshkent kuni muhim —
    shuning uchun Toshkent vaqtiga o'girib, kunini olamiz.
    """
    close = _application_close(program.deadlines)
    if close is not None:
        return DeadlineInfo(
            precision=DeadlinePrecision.EXACT,
            exact_date=close.date_utc.astimezone(TASHKENT_TZ).date(),
        )
    if program.deadline_month:
        return DeadlineInfo(precision=DeadlinePrecision.MONTH, month=program.deadline_month)
    return DeadlineInfo(precision=DeadlinePrecision.UNKNOWN)

def _application_close(deadlines: Iterable[Deadline]) -> Deadline | None:
    """Ariza yopilish sanasi. Bir nechta bo'lsa — eng keyingisi.

    Bir dasturda bosqichli muddatlar bo'lishi mumkin (masalan Manchester'da
    to'rtta bosqich). Oxirgisi — haqiqiy yopilish sanasi.
    """
    closes = [d for d in deadlines if d.type == DeadlineType.APPLICATION_CLOSE]
    return max(closes, key=lambda d: d.date_utc) if closes else None

def next_month_occurrence(month: int, today: date) -> date:
    """Berilgan oyning keyingi kelish sanasi (o'sha oyning 1-kuni).

    Oy bu yil allaqachon tugagan bo'lsa, keyingi yil olinadi. Dekabr ->
    yanvar o'tishi shu yerda hal bo'ladi.
    """
    candidate = date(today.year, month, 1)
    if _month_end(candidate) < today:
        candidate = date(today.year + 1, month, 1)
    return candidate

def _month_end(first_day: date) -> date:
    return first_day.replace(day=monthrange(first_day.year, first_day.month)[1])

def _previous_month_first(day: date) -> date:
    return (day - timedelta(days=1)).replace(day=1)

# ------------------------------------------------------------ rejalashtirish --

def plan_for_saved(saved: SavedProgram, today: date) -> list[PlannedMessage]:
    """Bitta saqlangan dastur uchun BUGUNGI kunga qadar yetilgan xabarlar.

    Qaytgan ro'yxat hali `notification_logs` bilan solishtirilmagan — allaqachon
    yuborilganlarini chaqiruvchi tomon filtrlaydi.
    """
    info = resolve_deadline(saved.program)

    if info.precision is DeadlinePrecision.EXACT:
        assert info.exact_date is not None
        # Muddati o'tgan dastur — "yopilgan", xabar yuborilmaydi.
        if info.exact_date < today:
            return []
        days_left = (info.exact_date - today).days
        plans = []
        for notif_type, offset in (
            (NotificationType.EXACT_14D, 14),
            (NotificationType.EXACT_3D, 3),
        ):
            due_on = info.exact_date - timedelta(days=offset)
            # "Aynan bugun" emas, "vaqti kelgan" — server bir kun o'chiq
            # tursa ham xabar yo'qolmaydi.
            if due_on <= today:
                plans.append(
                    PlannedMessage(
                        saved=saved,
                        notif_type=notif_type,
                        due_on=due_on,
                        deadline_date=info.exact_date,
                        days_left=days_left,
                    )
                )
        return plans

    if info.precision is DeadlinePrecision.MONTH:
        assert info.month is not None
        target = next_month_occurrence(info.month, today)
        plans = []
        for notif_type, due_on in (
            (NotificationType.MONTH_BEFORE, _previous_month_first(target)),
            (NotificationType.MONTH_START, target),
        ):
            if due_on <= today:
                plans.append(
                    PlannedMessage(
                        saved=saved, notif_type=notif_type, due_on=due_on, month=info.month
                    )
                )
        return plans

    due_on = saved.created_at.astimezone(TASHKENT_TZ).date() + timedelta(
        days=UNKNOWN_CHECK_AFTER_DAYS
    )
    if due_on <= today:
        return [
            PlannedMessage(
                saved=saved, notif_type=NotificationType.UNKNOWN_CHECK, due_on=due_on
            )
        ]
    return []

def user_accepts_reminders(user: User) -> bool:
    """Foydalanuvchiga umuman xabar yuborish mumkinmi."""
    return not user.is_blocked and user.notifications_enabled

def saved_accepts_reminders(saved: SavedProgram) -> bool:
    """Shu dastur bo'yicha eslatma yuborish mumkinmi.

    "Ariza berdim" belgilangan yoki eslatma o'chirilgan bo'lsa — yo'q.
    """
    return saved.reminders_active and saved.status is not SavedProgramStatus.APPLIED

def allowed_after_enabling(plan: PlannedMessage, user: User) -> bool:
    """Eslatmalar o'chiq turgan davrdagi xabarlar orqaga qarab yuborilmaydi.

    Faqat rejalashtirilgan sanasi `notifications_enabled_at` dan keyin yoki
    unga teng bo'lgan xabarlar o'tadi. Maydon bo'sh bo'lsa (eski
    foydalanuvchilar) hech narsa cheklanmaydi.
    """
    if user.notifications_enabled_at is None:
        return True
    return plan.due_on >= user.notifications_enabled_at.astimezone(TASHKENT_TZ).date()

# ----------------------------------------------------------------- tanlash --

async def collect_due(session: AsyncSession, today: date) -> list[PlannedMessage]:
    """Bugun yuborilishi kerak bo'lgan, hali yuborilmagan xabarlar."""
    stmt = select(SavedProgram).options(
        selectinload(SavedProgram.user),
        selectinload(SavedProgram.program).selectinload(Program.deadlines),
        selectinload(SavedProgram.program).selectinload(Program.university),
    )
    saved_programs = (await session.execute(stmt)).scalars().all()

    candidates: list[PlannedMessage] = []
    for saved in saved_programs:
        if not user_accepts_reminders(saved.user) or not saved_accepts_reminders(saved):
            continue
        for plan in plan_for_saved(saved, today):
            if allowed_after_enabling(plan, saved.user):
                candidates.append(plan)

    if not candidates:
        return []

    already = await _already_sent(session, candidates)
    return [
        plan
        for plan in candidates
        if (plan.saved.user_id, plan.saved.program_id, plan.notif_type) not in already
    ]

async def _already_sent(
    session: AsyncSession, plans: list[PlannedMessage]
) -> set[tuple[int, int, NotificationType]]:
    user_ids = {plan.saved.user_id for plan in plans}
    rows = (
        await session.execute(
            select(
                NotificationLog.user_id, NotificationLog.program_id, NotificationLog.notif_type
            ).where(NotificationLog.user_id.in_(user_ids))
        )
    ).all()
    return {(row[0], row[1], row[2]) for row in rows}

# ------------------------------------------------------------------ matnlar --

def message_line(plan: PlannedMessage, lang: str) -> str:
    """Bitta dastur uchun xabar matni."""
    program = plan.saved.program
    university = program.university.name if program.university else ""
    month_name = t(f"month.{plan.month}", lang) if plan.month else ""
    return t(
        f"notif.{plan.notif_type.value}",
        lang,
        program=program.name,
        university=university,
        date=plan.deadline_date.isoformat() if plan.deadline_date else "",
        days=plan.days_left if plan.days_left is not None else "",
        month=month_name,
    )

def _webapp(path: str) -> WebAppInfo | None:
    """Mini App'ning ichki sahifasiga havola (`startapp` o'rnini bosadi).

    `WebAppInfo` tugmasi `startapp` ni qabul qilmaydi — u faqat `t.me`
    havolasida ishlaydi. Shuning uchun parametr URL'ning o'ziga qo'shiladi,
    Mini App esa uni `location.hash` dan o'qiydi.
    """
    base = (settings.webapp_url or "").rstrip("/")
    if not base:
        return None
    return WebAppInfo(url=f"{base}/#{path}")

def program_buttons(plan: PlannedMessage, lang: str) -> list[list[InlineKeyboardButton]]:
    """Bitta dastur uchun tugmalar qatori."""
    program = plan.saved.program
    rows: list[list[InlineKeyboardButton]] = []

    first: list[InlineKeyboardButton] = []
    app_link = _webapp(f"program_{program.id}")
    if app_link is not None:
        first.append(InlineKeyboardButton(text=t("notif.btn_open", lang), web_app=app_link))
    if program.source_url:
        first.append(
            InlineKeyboardButton(text=t("notif.btn_site", lang), url=program.source_url)
        )
    if first:
        rows.append(first)

    rows.append(
        [
            InlineKeyboardButton(
                text=t("notif.btn_applied", lang), callback_data=f"applied:{program.id}"
            ),
            InlineKeyboardButton(
                text=t("notif.btn_mute", lang), callback_data=f"mute:{program.id}"
            ),
        ]
    )

    if plan.notif_type is NotificationType.UNKNOWN_CHECK:
        suggest = _webapp(f"suggest_{program.id}")
        if suggest is not None:
            rows.append(
                [InlineKeyboardButton(text=t("notif.btn_suggest", lang), web_app=suggest)]
            )
    return rows

def build_digest(plans: list[PlannedMessage], lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Bir foydalanuvchiga ketadigan BITTA jamlangan xabar.

    Bir kunda bir nechta dastur to'g'ri kelsa, alohida-alohida xabar yuborish
    spam bo'lardi: har bir dastur alohida qator, tugmalar esa dastur bo'yicha.
    """
    if len(plans) == 1:
        text = message_line(plans[0], lang)
        rows = program_buttons(plans[0], lang)
    else:
        lines = [t("notif.digest_header", lang), ""]
        rows = []
        for plan in plans:
            lines.append(message_line(plan, lang))
            lines.append("")
            rows.extend(program_buttons(plan, lang))
        text = "\n".join(lines).strip()

    settings_link = _webapp("profile")
    if settings_link is not None:
        rows.append(
            [InlineKeyboardButton(text=t("notif.btn_settings", lang), web_app=settings_link)]
        )
    return text, InlineKeyboardMarkup(inline_keyboard=rows)

# ----------------------------------------------------------------- yuborish --

async def send_digest(bot: Bot, user: User, plans: list[PlannedMessage]) -> bool:
    """Bitta foydalanuvchiga jamlangan xabarni yuboradi.

    Qaytadi: yuborildimi. 403 (bot bloklangan) da `is_blocked` qo'yiladi va
    False qaytadi; 429 da Telegram aytgan muddat kutilib, bir marta qayta
    urinadi.
    """
    text, markup = build_digest(plans, user.ui_language.value)
    try:
        await bot.send_message(user.telegram_id, text, reply_markup=markup)
    except TelegramForbiddenError:
        # Foydalanuvchi botni bloklagan — endi unga urinishning ma'nosi yo'q.
        user.is_blocked = True
        logger.info("Bot bloklangan: user_id=%s", user.id)
        return False
    except TelegramRetryAfter as exc:
        await asyncio.sleep(exc.retry_after)
        try:
            await bot.send_message(user.telegram_id, text, reply_markup=markup)
        except Exception:
            logger.exception("Qayta urinish ham muvaffaqiyatsiz: user_id=%s", user.id)
            return False
    except Exception:
        logger.exception("Eslatma yuborishda xatolik: user_id=%s", user.id)
        return False
    return True

async def mark_sent(session: AsyncSession, plans: Iterable[PlannedMessage]) -> None:
    session.add_all(
        NotificationLog(
            user_id=plan.saved.user_id,
            program_id=plan.saved.program_id,
            notif_type=plan.notif_type,
        )
        for plan in plans
    )

async def run_reminder_scan(
    bot: Bot | None,
    session: AsyncSession,
    *,
    today: date | None = None,
    dry_run: bool = False,
) -> ScanResult:
    """Bir marta to'liq tekshiruv: topadi, jamlaydi, yuboradi, belgilaydi."""
    today = today or datetime.now(TASHKENT_TZ).date()
    result = ScanResult()

    due = await collect_due(session, today)
    result.planned = due
    if not due:
        return result

    by_user: dict[int, list[PlannedMessage]] = {}
    for plan in due:
        by_user.setdefault(plan.saved.user_id, []).append(plan)

    for plans in by_user.values():
        user = plans[0].saved.user
        if dry_run:
            result.sent_users += 1
            result.sent_messages += len(plans)
            continue

        assert bot is not None, "dry_run bo'lmaganda bot kerak"
        ok = await send_digest(bot, user, plans)
        if not ok:
            if user.is_blocked:
                result.blocked_users += 1
            continue

        await mark_sent(session, plans)
        result.sent_users += 1
        result.sent_messages += len(plans)
        await asyncio.sleep(_SEND_INTERVAL)

    await session.commit()
    return result

# ------------------------------------------- saqlash paytidagi darhol xabar --

async def send_immediate_if_due(
    bot: Bot | None,
    session: AsyncSession,
    saved: SavedProgram,
    *,
    today: date | None = None,
) -> NotificationType | None:
    """Dastur saqlanganda deadline yaqin bo'lsa, o'sha zahoti xabar beradi.

    Rejalashtirilgan eslatma 14 kun qolganda ketadi — deadline'ga 5 kun
    qolganda saqlagan odam hech qanday xabar olmay qolardi. Shuning uchun:

      3 kundan kam  -> darhol yuboriladi, 14 va 3 kunliklari "yuborilgan"
                       deb belgilanadi (ular endi keraksiz)
      3-14 kun      -> darhol yuboriladi, 14 kunligi belgilanadi
                       (3 kunligi o'z vaqtida ketadi)
      14 kundan ko'p -> hech narsa

    Qaytadi: yuborilgan xabar turi yoki None.
    """
    today = today or datetime.now(TASHKENT_TZ).date()
    user = saved.user
    if not user_accepts_reminders(user) or not saved_accepts_reminders(saved):
        return None

    info = resolve_deadline(saved.program)
    if info.precision is not DeadlinePrecision.EXACT or info.exact_date is None:
        return None

    days_left = (info.exact_date - today).days
    if days_left < 0 or days_left > IMMEDIATE_SOON_DAYS:
        return None

    plan = PlannedMessage(
        saved=saved,
        notif_type=NotificationType.EXACT_IMMEDIATE,
        due_on=today,
        deadline_date=info.exact_date,
        days_left=days_left,
    )

    already = await _already_sent(session, [plan])
    key = (saved.user_id, saved.program_id, NotificationType.EXACT_IMMEDIATE)
    if key in already:
        return None

    if bot is not None:
        text, markup = build_digest([plan], user.ui_language.value)
        try:
            await bot.send_message(user.telegram_id, text, reply_markup=markup)
        except TelegramForbiddenError:
            user.is_blocked = True
            await session.commit()
            return None
        except Exception:
            logger.exception("Darhol xabar yuborilmadi: saved_id=%s", saved.id)
            return None

    suppressed = [NotificationType.EXACT_14D]
    if days_left < IMMEDIATE_URGENT_DAYS:
        suppressed.append(NotificationType.EXACT_3D)

    await mark_sent(session, [plan])
    await mark_sent(
        session,
        [
            PlannedMessage(saved=saved, notif_type=notif_type, due_on=today)
            for notif_type in suppressed
        ],
    )
    await session.commit()
    return NotificationType.EXACT_IMMEDIATE

# ------------------------------------------------------------ kunlik jadval --

def is_send_time(now_tashkent: datetime) -> bool:
    return now_tashkent.hour == DAILY_SEND_HOUR

def utc_now() -> datetime:
    return datetime.now(UTC)

__all__ = [
    "DAILY_SEND_HOUR",
    "IMMEDIATE_SOON_DAYS",
    "DeadlineInfo",
    "DeadlinePrecision",
    "PlannedMessage",
    "ScanResult",
    "build_digest",
    "collect_due",
    "is_send_time",
    "next_month_occurrence",
    "plan_for_saved",
    "resolve_deadline",
    "run_reminder_scan",
    "send_immediate_if_due",
    "utc_now",
]
