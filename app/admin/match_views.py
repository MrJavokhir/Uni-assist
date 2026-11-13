"""Admin: haftalik "sizga mos dastur topildi" xabarlari (app/services/match_notification_service.py).

Avtomatik yuborish har seshanba 10:00 da bot jarayonida ketadi. Bu sahifa
holatni ko'rsatadi, bot adminlariga namuna yuboradi va kerak bo'lsa
yuborishni hoziroq boshlaydi. Qo'lda yuborilgandan keyin seshanba kuni
o'sha userlarga takror ketmaydi (`RECENT_DAYS`).
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from sqladmin import BaseView, expose
from sqladmin.flash import Flash
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.auth import current_admin
from app.config import settings
from app.db.models import MatchNotification, Program, User
from app.db.session import async_session_factory
from app.services import match_notification_service as mns
from app.services import payment_service
from app.services.event_service import filter_is_complete
from app.services.timezone_utils import TASHKENT_TZ
from app.services.user_service import _PROFILE_RELATIONSHIPS

logger = logging.getLogger(__name__)

RECENT_LIMIT = 20
SAMPLE_SEARCH_LIMIT = 30
WEEKDAYS = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]

# Qo'lda boshlangan yuborish holati (jarayon ichida; qayta ishga tushsa yo'qoladi).
_run_state: dict = {"running": False, "started_at": None, "by": None, "result": None, "error": None}
_tasks: set[asyncio.Task] = set()


def _new_bot() -> Bot:
    return Bot(token=settings.bot_token)


async def _run_now(started_by: str) -> None:
    _run_state.update(
        running=True, started_at=datetime.now(UTC), by=started_by, result=None, error=None
    )
    bot = _new_bot()
    try:
        async with async_session_factory() as session:
            _run_state["result"] = await mns.run_match_scan(bot, session)
    except Exception as exc:
        logger.exception("Mos dastur xabarlarini qo'lda yuborishda xatolik")
        _run_state["error"] = str(exc)[:500]
    finally:
        _run_state["running"] = False
        await bot.session.close()


async def _sample_program(session, admin_user: User | None):
    """Namuna uchun dastur: adminning o'z filtri bo'yicha, bo'lmasa birinchi mos userniki."""
    if admin_user is not None and filter_is_complete(admin_user):
        program = await mns.pick_program(session, admin_user)
        if program is not None:
            return program, True
    for user in (await mns.eligible_users(session))[:SAMPLE_SEARCH_LIMIT]:
        program = await mns.pick_program(session, user)
        if program is not None:
            return program, False
    return None, False


class MatchNotifyView(BaseView):
    name = "Mos dastur xabarlari"
    identity = "match-notify"
    icon = "fa-solid fa-wand-magic-sparkles"

    def _back(self, request: Request) -> RedirectResponse:
        return RedirectResponse(str(request.url_for("admin:view-match-notify")), status_code=303)

    @expose("/match-notifications", methods=["GET"], identity="match-notify")
    async def page(self, request: Request):
        now = datetime.now(UTC)
        today = now.astimezone(TASHKENT_TZ).date()
        async with async_session_factory() as session:
            eligible = len(await mns.eligible_users(session))
            total = (
                await session.execute(select(func.count()).select_from(MatchNotification))
            ).scalar_one()
            week = (
                await session.execute(
                    select(func.count())
                    .select_from(MatchNotification)
                    .where(MatchNotification.sent_at >= now - timedelta(days=7))
                )
            ).scalar_one()
            rows = (
                await session.execute(
                    select(MatchNotification, User)
                    .join(User, User.id == MatchNotification.user_id)
                    .options(
                        selectinload(MatchNotification.program).selectinload(Program.university)
                    )
                    .order_by(MatchNotification.sent_at.desc())
                    .limit(RECENT_LIMIT)
                )
            ).all()
            admins = await payment_service.active_admin_ids(session)

        next_day = mns.next_match_day(today)
        if next_day == today and datetime.now(TASHKENT_TZ).hour >= 11:
            next_day = mns.next_match_day(today + timedelta(days=1))
        return await self.templates.TemplateResponse(
            request,
            "match_notify.html",
            {
                "title": "Mos dastur xabarlari",
                "subtitle": "Har seshanba userga tanlagan yo'nalishi bo'yicha eng mos dastur",
                "eligible": eligible,
                "total": total,
                "week": week,
                "next_day": f"{next_day.day:02d}.{next_day.month:02d}.{next_day.year}",
                "next_weekday": WEEKDAYS[next_day.weekday()],
                "recent_days": mns.RECENT_DAYS,
                "admins_count": len(admins),
                "state": _run_state,
                "recent": [
                    {
                        "at": m.sent_at.astimezone(TASHKENT_TZ),
                        "user": str(u),
                        "program": m.program.name,
                        "university": m.program.university.name,
                    }
                    for m, u in rows
                ],
            },
        )

    @expose("/match-notifications/test", methods=["POST"], identity="match-notify-test")
    async def test(self, request: Request):
        """Bot adminlariga namuna — hech kimga hisobga yozilmaydi."""
        today = datetime.now(TASHKENT_TZ).date()
        async with async_session_factory() as session:
            admins = await payment_service.active_admin_ids(session)
            if not admins:
                Flash.error(
                    request,
                    "Bot adminlari ro'yxati bo'sh — «Bot adminlari»ga o'z ID'ingizni qo'shing.",
                )
                return self._back(request)
            sent, errors, program_name = 0, [], None
            bot = _new_bot()
            try:
                for admin_id in admins:
                    admin_user = (
                        await session.execute(
                            select(User)
                            .options(
                                *(selectinload(getattr(User, r)) for r in _PROFILE_RELATIONSHIPS)
                            )
                            .where(User.telegram_id == admin_id)
                        )
                    ).scalar_one_or_none()
                    program, _own = await _sample_program(session, admin_user)
                    if program is None:
                        errors.append(
                            "Hech bir userga mos dastur topilmadi (katalog yoki filtrlar bo'sh)."
                        )
                        break
                    lang = admin_user.ui_language.value if admin_user else "uz"
                    try:
                        await mns.send_program(bot, admin_id, lang, program, today)
                        sent += 1
                        program_name = program.name
                    except Exception as exc:  # noqa: BLE001 — xato adminga ko'rsatiladi
                        errors.append(f"{admin_id}: {exc}")
            finally:
                await bot.session.close()
        if errors:
            Flash.error(request, "Namuna yuborilmadi: " + "; ".join(errors)[:500])
        else:
            Flash.success(request, f"Namuna {sent} ta bot adminiga yuborildi ({program_name}).")
        return self._back(request)

    @expose("/match-notifications/run", methods=["POST"], identity="match-notify-run")
    async def run(self, request: Request):
        form = await request.form()
        if form.get("confirm") != "yes":
            Flash.error(request, "Yuborishni tasdiqlang.")
            return self._back(request)
        if _run_state["running"]:
            Flash.error(request, "Yuborish allaqachon ketmoqda.")
            return self._back(request)
        task = asyncio.create_task(_run_now(current_admin(request)), name="match-notify-now")
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
        Flash.success(request, "Yuborish boshlandi. Natija shu sahifada chiqadi.")
        return self._back(request)
