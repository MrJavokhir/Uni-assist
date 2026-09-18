from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqladmin import BaseView, expose
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.admin.formatters import VERIFIED_STALE_DAYS
from app.admin.views import _DEGREE_LABELS
from app.db.models import (
    Country,
    Program,
    ProgramCost,
    ProgramRequirement,
    Report,
    ReportStatus,
    SavedProgram,
    Scholarship,
    University,
    User,
)
from app.db.session import async_session_factory

USER_CHART_DAYS = 14
STALE_LIST_LIMIT = 8
REPORT_LIST_LIMIT = 5
INCOMPLETE_LIST_LIMIT = 8


@dataclass
class StaleRecord:
    kind: str
    name: str
    verified_at: datetime
    verified_by: str
    days_old: int
    edit_url: str


async def _stale_records(session: AsyncSession, cutoff: datetime, now: datetime) -> list[StaleRecord]:
    programs = (
        await session.execute(
            select(Program.id, Program.name, Program.verified_at, Program.verified_by)
            .where(Program.verified_at < cutoff)
            .order_by(Program.verified_at)
            .limit(STALE_LIST_LIMIT)
        )
    ).all()
    scholarships = (
        await session.execute(
            select(Scholarship.id, Scholarship.name, Scholarship.verified_at, Scholarship.verified_by)
            .where(Scholarship.verified_at < cutoff)
            .order_by(Scholarship.verified_at)
            .limit(STALE_LIST_LIMIT)
        )
    ).all()

    records = [
        StaleRecord(
            kind="Dastur",
            name=row.name,
            verified_at=row.verified_at,
            verified_by=row.verified_by,
            days_old=(now - row.verified_at).days,
            edit_url=f"/admin/program/edit/{row.id}",
        )
        for row in programs
    ] + [
        StaleRecord(
            kind="Grant",
            name=row.name,
            verified_at=row.verified_at,
            verified_by=row.verified_by,
            days_old=(now - row.verified_at).days,
            edit_url=f"/admin/scholarship/edit/{row.id}",
        )
        for row in scholarships
    ]

    records.sort(key=lambda r: r.verified_at)
    return records[:STALE_LIST_LIMIT]


class StatsView(BaseView):
    name = "Boshqaruv paneli"
    identity = "statistics"
    icon = "fa-solid fa-gauge-high"

    @expose("/statistics", methods=["GET"])
    async def statistics(self, request: Request):
        now = datetime.now(UTC)
        stale_cutoff = now - timedelta(days=VERIFIED_STALE_DAYS)
        chart_from = (now - timedelta(days=USER_CHART_DAYS - 1)).date()

        async with async_session_factory() as session:
            async def count(model) -> int:
                return (await session.execute(select(func.count(model.id)))).scalar_one()

            total_users = await count(User)
            total_universities = await count(University)
            total_programs = await count(Program)
            total_scholarships = await count(Scholarship)
            total_saved = await count(SavedProgram)

            open_reports = (
                await session.execute(
                    select(func.count(Report.id)).where(Report.status == ReportStatus.NEW)
                )
            ).scalar_one()

            stale_programs = (
                await session.execute(
                    select(func.count(Program.id)).where(Program.verified_at < stale_cutoff)
                )
            ).scalar_one()
            stale_scholarships = (
                await session.execute(
                    select(func.count(Scholarship.id)).where(Scholarship.verified_at < stale_cutoff)
                )
            ).scalar_one()

            signup_rows = (
                await session.execute(
                    select(func.date(User.created_at).label("day"), func.count(User.id))
                    .where(func.date(User.created_at) >= chart_from)
                    .group_by("day")
                    .order_by("day")
                )
            ).all()

            country_rows = (
                await session.execute(
                    select(Country.name_uz, func.count(Program.id))
                    .select_from(Program)
                    .join(University, University.id == Program.university_id)
                    .join(Country, Country.id == University.country_id)
                    .group_by(Country.name_uz)
                    .order_by(func.count(Program.id).desc())
                )
            ).all()

            # Shablonda lazy-load bo'lmasligi uchun kerakli ustunlarni darhol olamiz
            # (sessiya yopilgach relationship'ga murojaat qilish xato beradi).
            recent_reports = (
                await session.execute(
                    select(
                        Report.id,
                        Report.comment,
                        Report.created_at,
                        Program.name.label("program_name"),
                        Scholarship.name.label("scholarship_name"),
                    )
                    .outerjoin(Program, Program.id == Report.program_id)
                    .outerjoin(Scholarship, Scholarship.id == Report.scholarship_id)
                    .where(Report.status == ReportStatus.NEW)
                    .order_by(Report.created_at.desc())
                    .limit(REPORT_LIST_LIMIT)
                )
            ).all()

            stale_records = await _stale_records(session, stale_cutoff, now)

            # Talab yoki xarajat ma'lumoti yo'q dasturlar — seed orqali kiritilgan
            # yozuvlar aynan shu holatda bo'ladi va qo'lda to'ldirilishi kerak.
            incomplete_stmt = (
                select(
                    Program.id,
                    Program.name,
                    Program.degree_level,
                    University.name.label("university"),
                )
                .join(University, University.id == Program.university_id)
                .outerjoin(ProgramRequirement, ProgramRequirement.program_id == Program.id)
                .outerjoin(ProgramCost, ProgramCost.program_id == Program.id)
                .where(or_(ProgramRequirement.id.is_(None), ProgramCost.id.is_(None)))
                .order_by(Program.id)
            )
            incomplete_total = (
                await session.execute(
                    select(func.count()).select_from(incomplete_stmt.subquery())
                )
            ).scalar_one()
            incomplete_programs = (
                await session.execute(incomplete_stmt.limit(INCOMPLETE_LIST_LIMIT))
            ).all()

        signups = {row.day: row[1] for row in signup_rows}
        chart_labels = []
        chart_values = []
        for offset in range(USER_CHART_DAYS):
            day = chart_from + timedelta(days=offset)
            chart_labels.append(day.strftime("%d.%m"))
            chart_values.append(signups.get(day, 0))

        return await self.templates.TemplateResponse(
            request,
            "stats.html",
            {
                "title": "Boshqaruv paneli",
                "subtitle": "Katalog holati, ma'lumot sifati va foydalanuvchi faolligi",
                "total_users": total_users,
                "total_universities": total_universities,
                "total_programs": total_programs,
                "total_scholarships": total_scholarships,
                "total_saved": total_saved,
                "open_reports": open_reports,
                "stale_total": stale_programs + stale_scholarships,
                "stale_days": VERIFIED_STALE_DAYS,
                "chart_labels": chart_labels,
                "chart_values": chart_values,
                "country_labels": [row[0] for row in country_rows],
                "country_values": [row[1] for row in country_rows],
                "stale_records": stale_records,
                "recent_reports": recent_reports,
                "incomplete_total": incomplete_total,
                "incomplete_programs": incomplete_programs,
                "degree_labels": _DEGREE_LABELS,
            },
        )
