from sqladmin import BaseView, expose
from sqlalchemy import func, select
from starlette.requests import Request

from app.db.models import Country, Report, ReportStatus, SavedProgram, User, user_target_country
from app.db.session import async_session_factory


class StatsView(BaseView):
    name = "Statistika"
    identity = "statistics"
    icon = "fa-solid fa-chart-simple"
    category = "Statistika"

    @expose("/statistics", methods=["GET"])
    async def statistics(self, request: Request):
        async with async_session_factory() as session:
            total_users = (await session.execute(select(func.count(User.id)))).scalar_one()
            total_saved = (await session.execute(select(func.count(SavedProgram.id)))).scalar_one()
            open_reports = (
                await session.execute(
                    select(func.count(Report.id)).where(Report.status == ReportStatus.NEW)
                )
            ).scalar_one()

            country_rows = (
                await session.execute(
                    select(Country.name_uz, func.count(user_target_country.c.user_id))
                    .select_from(user_target_country)
                    .join(Country, Country.id == user_target_country.c.country_id)
                    .group_by(Country.name_uz)
                    .order_by(func.count(user_target_country.c.user_id).desc())
                )
            ).all()

        return await self.templates.TemplateResponse(
            request,
            "stats.html",
            {
                "title": "Statistika",
                "subtitle": "Bot va katalog bo'yicha umumiy ko'rsatkichlar",
                "total_users": total_users,
                "total_saved": total_saved,
                "open_reports": open_reports,
                "country_rows": country_rows,
            },
        )
