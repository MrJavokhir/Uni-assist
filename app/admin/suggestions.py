"""Foydalanuvchilar taklif qilgan deadline sanalari.

Taklif katalogga TO'G'RIDAN-TO'G'RI tushmaydi. Loyihaning qoidasi: har bir
sana rasmiy manbaga asoslanishi kerak, foydalanuvchi esa adashishi yoki
boshqa qabul oqimining sanasini yozishi mumkin. Shuning uchun admin uni
tasdiqlaydi — shundagina `deadlines` jadvaliga tushadi.
"""

import logging
from datetime import UTC, datetime, time

from sqladmin import BaseView, expose
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.db.models import (
    Deadline,
    DeadlineSuggestion,
    DeadlineType,
    Program,
    SuggestionStatus,
)
from app.db.session import async_session_factory
from app.services.timezone_utils import TASHKENT_TZ

logger = logging.getLogger(__name__)


class SuggestionView(BaseView):
    name = "Taklif qilingan sanalar"
    identity = "deadline-suggestions"
    icon = "fa-solid fa-calendar-plus"

    @expose("/deadline-suggestions", methods=["GET", "POST"])
    async def page(self, request: Request):
        async with async_session_factory() as session:
            if request.method == "POST":
                form = await request.form()
                await self._act(session, form.get("action"), form.get("id"))
                await session.commit()
                return RedirectResponse(request.url.path, status_code=303)

            rows = (
                (
                    await session.execute(
                        select(DeadlineSuggestion)
                        .where(DeadlineSuggestion.status == SuggestionStatus.PENDING)
                        .options(
                            selectinload(DeadlineSuggestion.program).selectinload(
                                Program.university
                            ),
                            selectinload(DeadlineSuggestion.user),
                        )
                        .order_by(DeadlineSuggestion.created_at)
                    )
                )
                .scalars()
                .all()
            )

        return await self.templates.TemplateResponse(
            request,
            "suggestions.html",
            {
                "title": "Taklif qilingan sanalar",
                "subtitle": "Foydalanuvchilar yuborgan deadline sanalari",
                "rows": rows,
            },
        )

    async def _act(self, session, action: str | None, raw_id: str | None) -> None:
        if not (raw_id or "").isdigit():
            return
        suggestion = await session.get(DeadlineSuggestion, int(raw_id))
        if suggestion is None or suggestion.status is not SuggestionStatus.PENDING:
            return

        if action == "reject":
            suggestion.status = SuggestionStatus.REJECTED
            return

        if action != "approve":
            return

        program = await session.get(
            Program, suggestion.program_id, options=[selectinload(Program.deadlines)]
        )
        if program is None:
            suggestion.status = SuggestionStatus.REJECTED
            return

        # Sana Toshkent kuni sifatida tushunarli bo'lishi uchun o'sha
        # mintaqaning peshinida saqlanadi — UTC'ga o'girilganda ham
        # kun o'zgarmaydi.
        moment = datetime.combine(suggestion.suggested_date, time(12, 0), tzinfo=TASHKENT_TZ)
        existing = next(
            (d for d in program.deadlines if d.type == DeadlineType.APPLICATION_CLOSE), None
        )
        if existing is not None:
            existing.date_utc = moment.astimezone(UTC)
        else:
            session.add(
                Deadline(
                    program_id=program.id,
                    type=DeadlineType.APPLICATION_CLOSE,
                    date_utc=moment.astimezone(UTC),
                    intake_term=program.intake_term,
                )
            )
        # Oy darajasidagi taxmin endi keraksiz: aniq sana paydo bo'ldi.
        program.deadline_month = None
        suggestion.status = SuggestionStatus.APPROVED

        # Shu dastur bo'yicha boshqa kutilayotgan takliflar yopiladi —
        # sana allaqachon aniqlandi.
        others = (
            (
                await session.execute(
                    select(DeadlineSuggestion).where(
                        DeadlineSuggestion.program_id == program.id,
                        DeadlineSuggestion.status == SuggestionStatus.PENDING,
                        DeadlineSuggestion.id != suggestion.id,
                    )
                )
            )
            .scalars()
            .all()
        )
        for other in others:
            other.status = SuggestionStatus.REJECTED
