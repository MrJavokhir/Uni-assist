from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from sqladmin import BaseView, expose
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.admin.formatters import VERIFIED_STALE_DAYS
from app.admin.views import _DEGREE_LABELS
from app.db.models import (
    Country,
    DeadlineSuggestion,
    Field,
    NotificationLog,
    Program,
    SavedProgram,
    SavedProgramStatus,
    Scholarship,
    SuggestionStatus,
    University,
    User,
    user_target_country,
)
from app.db.session import async_session_factory
from app.services.timezone_utils import TASHKENT_TZ

USER_CHART_DAYS = 14
STALE_LIST_LIMIT = 8
# Talabni ko'rsatadigan ro'yxatlar uzunligi: 8 tadan keyin quyruq juda
# yupqalashadi va grafik o'qilmay qoladi.
TOP_DEMAND_LIMIT = 8


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

            # --- Deadline eslatmalari ---
            # "Bugun" Toshkent kuni bo'yicha: eslatmalar ham o'sha vaqtda
            # yuboriladi, shuning uchun UTC kuni chalg'itardi.
            today_start = datetime.combine(
                datetime.now(TASHKENT_TZ).date(), time.min, tzinfo=TASHKENT_TZ
            )
            week_start = today_start - timedelta(days=6)

            async def notif_stats(since: datetime) -> tuple[int, int]:
                row = (
                    await session.execute(
                        select(
                            func.count(NotificationLog.id),
                            func.count(NotificationLog.id).filter(NotificationLog.clicked),
                        ).where(NotificationLog.sent_at >= since)
                    )
                ).one()
                return int(row[0] or 0), int(row[1] or 0)

            notif_today, notif_today_clicked = await notif_stats(today_start)
            notif_week, notif_week_clicked = await notif_stats(week_start)

            blocked_users = (
                await session.execute(
                    select(func.count(User.id)).where(User.is_blocked.is_(True))
                )
            ).scalar_one()
            notif_off_users = (
                await session.execute(
                    select(func.count(User.id)).where(User.notifications_enabled.is_(False))
                )
            ).scalar_one()
            applied_count = (
                await session.execute(
                    select(func.count(SavedProgram.id)).where(
                        SavedProgram.status == SavedProgramStatus.APPLIED
                    )
                )
            ).scalar_one()
            pending_suggestions = (
                await session.execute(
                    select(func.count(DeadlineSuggestion.id)).where(
                        DeadlineSuggestion.status == SuggestionStatus.PENDING
                    )
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

            stale_records = await _stale_records(session, stale_cutoff, now)

            # Foydalanuvchilar NIMA qidirayotgani. Bu qidiruv jurnali emas —
            # bunday jurnal yuritilmaydi. Manba: profildagi filtr tanlovlari,
            # ya'ni odam o'zi uchun belgilab qo'ygan davlat va yo'nalish.
            # Katalogni qayerga kengaytirish kerakligini aynan shu ko'rsatadi.
            demand_country_rows = (
                await session.execute(
                    select(Country.name_uz, func.count(user_target_country.c.user_id))
                    .select_from(user_target_country)
                    .join(Country, Country.id == user_target_country.c.country_id)
                    .group_by(Country.name_uz)
                    .order_by(func.count(user_target_country.c.user_id).desc())
                    .limit(TOP_DEMAND_LIMIT)
                )
            ).all()
            demand_field_rows = (
                await session.execute(
                    select(Field.name_uz, func.count(User.id))
                    .select_from(User)
                    .join(Field, Field.id == User.field_id)
                    .group_by(Field.name_uz)
                    .order_by(func.count(User.id).desc())
                    .limit(TOP_DEMAND_LIMIT)
                )
            ).all()

            demand_degree_rows = (
                await session.execute(
                    select(User.degree_level, func.count(User.id))
                    .where(User.degree_level.is_not(None))
                    .group_by(User.degree_level)
                    .order_by(func.count(User.id).desc())
                )
            ).all()

            # Namuna hajmi: foiz emas, "nechta odam tanlagan" degan son.
            # Usiz birinchi o'rindagi davlat 3 ta odamdan kelganini bilib
            # bo'lmasdi va raqamga ortiqcha ishonilardi.
            country_choosers = (
                await session.execute(
                    select(func.count(func.distinct(user_target_country.c.user_id)))
                )
            ).scalar_one()
            field_choosers = (
                await session.execute(
                    select(func.count(User.id)).where(User.field_id.is_not(None))
                )
            ).scalar_one()
            degree_choosers = sum(row[1] for row in demand_degree_rows)

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
                "notif_today": notif_today,
                "notif_today_clicked": notif_today_clicked,
                "notif_week": notif_week,
                "notif_week_clicked": notif_week_clicked,
                "notif_click_rate": (
                    round(notif_week_clicked * 100 / notif_week) if notif_week else 0
                ),
                "blocked_users": blocked_users,
                "notif_off_users": notif_off_users,
                "applied_count": applied_count,
                "pending_suggestions": pending_suggestions,
                "stale_total": stale_programs + stale_scholarships,
                "stale_days": VERIFIED_STALE_DAYS,
                "chart_labels": chart_labels,
                "chart_values": chart_values,
                "country_labels": [row[0] for row in country_rows],
                "country_values": [row[1] for row in country_rows],
                "stale_records": stale_records,
                "demand_country_labels": [row[0] for row in demand_country_rows],
                "demand_country_values": [row[1] for row in demand_country_rows],
                "demand_field_labels": [row[0] for row in demand_field_rows],
                "demand_field_values": [row[1] for row in demand_field_rows],
                # Daraja enum bo'lgani uchun yorliq shu yerda o'giriladi —
                # shablonga tayyor matn boradi.
                "demand_degree_labels": [
                    _DEGREE_LABELS.get(row[0], row[0].value) for row in demand_degree_rows
                ],
                "demand_degree_values": [row[1] for row in demand_degree_rows],
                "country_choosers": country_choosers,
                "field_choosers": field_choosers,
                "degree_choosers": degree_choosers,
                "degree_labels": _DEGREE_LABELS,
            },
        )
