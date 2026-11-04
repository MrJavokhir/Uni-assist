"""Dastur va grant sahifalarini ko'rishlar.

Sahifada necha soniya turganini Mini App o'lchaydi (`VIEW_AFTER_MS`,
app/webapp/static/app.js) va shundan keyingina shu yerga murojaat qiladi.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentView, Program, Scholarship, University, User
from app.services.timezone_utils import TASHKENT_TZ

VIEW_PROGRAM = "program"
VIEW_GRANT = "grant"


@dataclass(frozen=True)
class TopItem:
    id: int
    name: str
    detail: str | None
    views: int


def _today(now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)).astimezone(TASHKENT_TZ).date()


async def count_for(session: AsyncSession, kind: str, target_id: int) -> int:
    stmt = select(func.count()).where(ContentView.kind == kind, ContentView.target_id == target_id)
    return (await session.execute(stmt)).scalar_one()


async def counts_for(session: AsyncSession, kind: str) -> dict[int, int]:
    stmt = (
        select(ContentView.target_id, func.count())
        .where(ContentView.kind == kind)
        .group_by(ContentView.target_id)
    )
    return dict((await session.execute(stmt)).all())


async def record(
    session: AsyncSession, user: User, kind: str, target_id: int, now: datetime | None = None
) -> int:
    """Ko'rishni yozadi (kuniga bir marta) va sahifaning jami sonini qaytaradi."""
    await session.execute(
        insert(ContentView)
        .values(kind=kind, target_id=target_id, user_id=user.id, day=_today(now))
        .on_conflict_do_nothing()
    )
    await session.commit()
    return await count_for(session, kind, target_id)


async def top_programs(session: AsyncSession, limit: int) -> list[TopItem]:
    views = func.count().label("views")
    stmt = (
        select(Program.id, Program.name, University.name, views)
        .select_from(ContentView)
        .join(Program, Program.id == ContentView.target_id)
        .join(University, University.id == Program.university_id)
        .where(ContentView.kind == VIEW_PROGRAM)
        .group_by(Program.id, Program.name, University.name)
        .order_by(views.desc(), Program.id)
        .limit(limit)
    )
    return [TopItem(*row) for row in await session.execute(stmt)]


async def top_grants(session: AsyncSession, limit: int) -> list[TopItem]:
    views = func.count().label("views")
    stmt = (
        select(Scholarship.id, Scholarship.name, views)
        .select_from(ContentView)
        .join(Scholarship, Scholarship.id == ContentView.target_id)
        .where(ContentView.kind == VIEW_GRANT)
        .group_by(Scholarship.id, Scholarship.name)
        .order_by(views.desc(), Scholarship.id)
        .limit(limit)
    )
    return [TopItem(id_, name, None, count) for id_, name, count in await session.execute(stmt)]


async def totals(
    session: AsyncSession, kind: str, now: datetime | None = None
) -> tuple[int, int]:
    """Shu turdagi sahifalarning jami va bugungi ko'rishlari."""
    stmt = select(func.count(), func.count().filter(ContentView.day == _today(now))).where(
        ContentView.kind == kind
    )
    total, today = (await session.execute(stmt)).one()
    return total, today
