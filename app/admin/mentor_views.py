"""Mentordan so'rash — adminka.

FAQAT uchta sahifa: savollar ro'yxati, savol sahifasi va shikoyatlar.
Mentorlarni boshqarish bo'limi ATAYLAB YO'Q: mentorni guruhga admin
Telegram'da qo'lda qo'shadi va chiqaradi, guruh a'zoligining o'zi
mentorlik huquqi (qarang: app/db/models/mentor.py).

Mentorning ismi va Telegram ID'si FAQAT shu yerda ko'rinadi —
foydalanuvchiga hech qachon berilmaydi.
"""

import logging
from datetime import date, datetime, time, timedelta

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqladmin import BaseView, expose
from sqladmin.flash import Flash
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import settings
from app.db.models import (
    ComplaintStatus,
    MentorComplaint,
    MentorQuestion,
    MentorQuestionStatus,
)
from app.db.session import async_session_factory
from app.services import mentor_group, mentor_service
from app.services.timezone_utils import TASHKENT_TZ, to_tashkent

logger = logging.getLogger(__name__)

CATEGORY = "Mentordan so'rash"
LIST_LIMIT = 200

STATUS_LABELS = {
    "open": ("Ochiq", "bg-yellow-lt"),
    "claimed": ("Javob yozilmoqda", "bg-blue-lt"),
    "answered": ("Javob berildi", "bg-green-lt"),
    "closed": ("Yopildi", "bg-secondary-lt"),
}
LEVEL_LABELS = {k.value: v for k, v in mentor_group.LEVEL_LABELS.items()}
TOPIC_LABELS = {k.value: v for k, v in mentor_group.TOPIC_LABELS.items()}
COMPLAINT_LABELS = {k.value: v for k, v in mentor_group.COMPLAINT_LABELS.items()}


def _int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def duration_label(delta: timedelta | None) -> str:
    """"2 soat 15 daq" — adminkadagi javob vaqti."""
    if delta is None:
        return "—"
    minutes = max(int(delta.total_seconds() // 60), 0)
    days, rest = divmod(minutes, 24 * 60)
    hours, mins = divmod(rest, 60)
    if days:
        return f"{days} kun {hours} soat"
    if hours:
        return f"{hours} soat {mins} daq"
    return f"{mins} daq"


def _fmt(moment: datetime | None) -> str:
    return to_tashkent(moment).strftime("%d.%m.%Y %H:%M") if moment else "—"


async def question_stats(session) -> dict:
    """Ro'yxat tepasidagi raqamlar (filtrdan qat'i nazar — umumiy holat)."""
    total = (await session.execute(select(func.count(MentorQuestion.id)))).scalar_one()
    answered = (
        await session.execute(
            select(func.count(MentorQuestion.id)).where(MentorQuestion.answered_at.is_not(None))
        )
    ).scalar_one()
    avg_seconds = (
        await session.execute(
            select(
                func.avg(
                    func.extract("epoch", MentorQuestion.answered_at - MentorQuestion.created_at)
                )
            ).where(MentorQuestion.answered_at.is_not(None))
        )
    ).scalar_one()
    unanswered = (
        await session.execute(
            select(func.count(MentorQuestion.id)).where(
                MentorQuestion.answered_at.is_(None),
                MentorQuestion.status != MentorQuestionStatus.CLOSED,
            )
        )
    ).scalar_one()
    return {
        "total": total,
        "answered_pct": round(answered * 100 / total) if total else 0,
        "avg_answer": duration_label(
            timedelta(seconds=float(avg_seconds)) if avg_seconds is not None else None
        ),
        "unanswered": unanswered,
    }


def _bot() -> Bot | None:
    if not settings.bot_token:
        return None
    return Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


class MentorQuestionsView(BaseView):
    name = "Savollar"
    identity = "mentor-questions"
    icon = "fa-solid fa-comments"
    category = CATEGORY

    @expose("/mentor-questions", methods=["GET"], identity="mentor-questions")
    async def page(self, request: Request):
        params = request.query_params
        country = (params.get("country") or "").upper()
        status = params.get("status") or ""
        date_from = _date(params.get("from"))
        date_to = _date(params.get("to"))

        stmt = select(MentorQuestion).order_by(MentorQuestion.created_at.desc())
        if country:
            stmt = stmt.where(MentorQuestion.country_code == country)
        if status in STATUS_LABELS:
            stmt = stmt.where(MentorQuestion.status == MentorQuestionStatus(status))
        if date_from:
            start = datetime.combine(date_from, time.min, tzinfo=TASHKENT_TZ)
            stmt = stmt.where(MentorQuestion.created_at >= start)
        if date_to:
            end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=TASHKENT_TZ)
            stmt = stmt.where(MentorQuestion.created_at < end)

        async with async_session_factory() as session:
            questions = (await session.execute(stmt.limit(LIST_LIMIT))).scalars().all()
            stats = await question_stats(session)
            countries = (
                (
                    await session.execute(
                        select(MentorQuestion.country_code)
                        .distinct()
                        .order_by(MentorQuestion.country_code)
                    )
                )
                .scalars()
                .all()
            )

        rows = [
            {
                "id": q.id,
                "number": q.public_number,
                "country": f"{mentor_group.flag(q.country_code)} {q.country_code}",
                "level": LEVEL_LABELS[q.level.value],
                "topic": TOPIC_LABELS[q.topic.value],
                "status": STATUS_LABELS[q.status.value],
                "created": _fmt(q.created_at),
                "answer_time": duration_label(
                    q.answered_at - q.created_at if q.answered_at else None
                ),
                "rating": q.rating,
            }
            for q in questions
        ]
        return await self.templates.TemplateResponse(
            request,
            "mentor_questions.html",
            {
                "title": "Mentor savollari",
                "rows": rows,
                "stats": stats,
                "countries": sorted(set(countries) | set(settings.active_country_codes)),
                "statuses": STATUS_LABELS,
                "filters": {
                    "country": country,
                    "status": status,
                    "from": params.get("from") or "",
                    "to": params.get("to") or "",
                },
                "limit": LIST_LIMIT,
            },
        )

    @expose("/mentor-question", methods=["GET"], identity="mentor-question")
    async def detail(self, request: Request):
        question_id = _int(request.query_params.get("id"))
        async with async_session_factory() as session:
            question = (
                await session.execute(
                    select(MentorQuestion)
                    .where(MentorQuestion.id == question_id)
                    .options(
                        selectinload(MentorQuestion.messages),
                        selectinload(MentorQuestion.complaints),
                        selectinload(MentorQuestion.user),
                    )
                )
            ).scalar_one_or_none()
            if question is None:
                Flash.error(request, "Savol topilmadi.")
                return RedirectResponse(request.url_for("admin:view-mentor-questions"), 303)
            country = await mentor_group.get_country(session, question.country_code)

        return await self.templates.TemplateResponse(
            request,
            "mentor_question.html",
            {
                "title": f"Savol #{question.public_number}",
                "q": question,
                "country": f"{mentor_group.flag(question.country_code)} "
                f"{mentor_group.country_name(country, 'uz', question.country_code)}",
                "level": LEVEL_LABELS[question.level.value],
                "topic": TOPIC_LABELS[question.topic.value],
                "status": STATUS_LABELS[question.status.value],
                "created": _fmt(question.created_at),
                "answered": _fmt(question.answered_at),
                "closed": _fmt(question.closed_at),
                "answer_time": duration_label(
                    question.answered_at - question.created_at if question.answered_at else None
                ),
                "messages": [
                    {
                        "sender": m.sender.value,
                        "text": m.text,
                        "time": _fmt(m.created_at),
                        "mentor_name": m.mentor_name,
                        "mentor_tg_id": m.mentor_tg_id,
                    }
                    for m in question.messages
                ],
                "complaints": [
                    {
                        "reason": COMPLAINT_LABELS[c.reason.value],
                        "comment": c.comment,
                        "time": _fmt(c.created_at),
                        "status": c.status.value,
                    }
                    for c in question.complaints
                ],
                "can_close": question.status != MentorQuestionStatus.CLOSED,
            },
        )

    @expose("/mentor-question/close", methods=["POST"], identity="mentor-question-close")
    async def close(self, request: Request):
        form = await request.form()
        question_id = _int(form.get("question_id"))
        back = RedirectResponse(
            str(request.url_for("admin:view-mentor-question").include_query_params(id=question_id)),
            status_code=303,
        )
        async with async_session_factory() as session:
            question = (
                await mentor_service.get_question(session, question_id) if question_id else None
            )
            if question is None:
                Flash.error(request, "Savol topilmadi.")
                return back
            bot = _bot() if settings.mentor_group_id else None
            try:
                if bot is not None:
                    # Admin yopganda foydalanuvchidan baho so'ralmaydi:
                    # odatda bu qoidabuzarlik yoki eskirgan savol.
                    closed = await mentor_group.close_question(
                        bot, session, question, ask_rating=False
                    )
                else:
                    closed = await mentor_service.close(session, question)
                await session.commit()
            finally:
                if bot is not None:
                    await bot.session.close()
        if closed:
            Flash.success(request, f"Savol #{question.public_number} yopildi.")
        else:
            Flash.info(request, "Savol allaqachon yopilgan.")
        return back


class MentorComplaintsView(BaseView):
    name = "Shikoyatlar"
    identity = "mentor-complaints"
    icon = "fa-solid fa-triangle-exclamation"
    category = CATEGORY

    @expose("/mentor-complaints", methods=["GET"], identity="mentor-complaints")
    async def page(self, request: Request):
        show_all = request.query_params.get("all") == "1"
        stmt = (
            select(MentorComplaint)
            .options(selectinload(MentorComplaint.question))
            .order_by(MentorComplaint.status, MentorComplaint.created_at.desc())
        )
        if not show_all:
            stmt = stmt.where(MentorComplaint.status == ComplaintStatus.NEW)
        async with async_session_factory() as session:
            complaints = (await session.execute(stmt.limit(LIST_LIMIT))).scalars().all()
            new_count = (
                await session.execute(
                    select(func.count(MentorComplaint.id)).where(
                        MentorComplaint.status == ComplaintStatus.NEW
                    )
                )
            ).scalar_one()

        rows = [
            {
                "id": c.id,
                "question_id": c.question_id,
                "number": c.question.public_number,
                "reason": COMPLAINT_LABELS[c.reason.value],
                "comment": c.comment,
                "time": _fmt(c.created_at),
                "is_new": c.status == ComplaintStatus.NEW,
                "on_message": c.message_id is not None,
            }
            for c in complaints
        ]
        return await self.templates.TemplateResponse(
            request,
            "mentor_complaints.html",
            {
                "title": "Shikoyatlar",
                "rows": rows,
                "show_all": show_all,
                "new_count": new_count,
            },
        )

    @expose("/mentor-complaints/review", methods=["POST"], identity="mentor-complaints-review")
    async def review(self, request: Request):
        form = await request.form()
        complaint_id = _int(form.get("complaint_id"))
        url = request.url_for("admin:view-mentor-complaints")
        if form.get("all") == "1":
            url = url.include_query_params(all="1")
        async with async_session_factory() as session:
            complaint = await session.get(MentorComplaint, complaint_id) if complaint_id else None
            if complaint is not None:
                complaint.status = ComplaintStatus.REVIEWED
                await session.commit()
        return RedirectResponse(str(url), status_code=303)
