"""Foydalanuvchi faolligi: oxirgi kirish va faol kunlar jurnali."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.filters import ActivityFilter
from app.admin.formatters import format_last_seen
from app.db.models import User, UserActivityDay
from app.services.activity_service import touch
from app.services.user_service import get_or_create_user


async def _days(session: AsyncSession) -> list:
    return (await session.execute(select(UserActivityDay.day))).scalars().all()


async def test_each_request_marks_user_active(session: AsyncSession) -> None:
    user = await get_or_create_user(session, 4242, "ali")

    assert user.last_seen_at is not None
    assert len(await _days(session)) == 1


async def test_touch_is_throttled_and_logs_one_row_per_day(session: AsyncSession) -> None:
    user = User(telegram_id=1)
    session.add(user)
    await session.commit()
    morning = datetime(2027, 3, 10, 4, 0, tzinfo=UTC)  # Toshkentda 09:00

    await touch(session, user, now=morning)
    await touch(session, user, now=morning + timedelta(minutes=2))
    assert user.last_seen_at == morning  # 5 daqiqa ichida yozilmaydi

    await touch(session, user, now=morning + timedelta(hours=3))
    assert user.last_seen_at == morning + timedelta(hours=3)
    assert len(await _days(session)) == 1  # o'sha kun — yangi qator yo'q

    await touch(session, user, now=morning + timedelta(days=1))
    assert len(await _days(session)) == 2


async def test_activity_filter(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    session.add_all(
        [
            User(telegram_id=1, last_seen_at=now),
            User(telegram_id=2, last_seen_at=now - timedelta(days=10)),
            User(telegram_id=3, last_seen_at=now - timedelta(days=45)),
            User(telegram_id=4),
        ]
    )
    await session.commit()

    async def ids(value: str) -> list[int]:
        query = await ActivityFilter().get_filtered_query(select(User), value, User)
        rows = (await session.execute(query.order_by(User.telegram_id))).scalars().all()
        return [row.telegram_id for row in rows]

    assert await ids("7d") == [1]
    assert await ids("30d") == [1, 2]
    assert await ids("inactive") == [3]
    assert await ids("never") == [4]


def test_last_seen_badges() -> None:
    now = datetime.now(UTC)
    assert "Faol" in format_last_seen(User(last_seen_at=now), "last_seen_at")
    assert "Kam faol" in format_last_seen(
        User(last_seen_at=now - timedelta(days=12)), "last_seen_at"
    )
    assert "Nofaol" in format_last_seen(User(last_seen_at=now - timedelta(days=60)), "last_seen_at")
    assert "Kuzatilmagan" in format_last_seen(User(), "last_seen_at")
