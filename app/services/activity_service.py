"""Foydalanuvchi faolligi: oxirgi kirish vaqti va faol kunlar jurnali.

Har bir murojaat (Mini App so'rovi yoki botdagi amal) `get_or_create_user`
orqali o'tadi va shu yerda belgilanadi. Bazaga har so'rovda yozilmaydi —
`TOUCH_EVERY` ichida qayta kelgan so'rov hech narsa o'zgartirmaydi.

`user_activity_days` — kuniga bitta qator: admin paneldagi "faol
foydalanuvchilar" grafigi shundan chiziladi (oxirgi kirish vaqtining o'zi
faqat eng so'nggi kunni biladi).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserActivityDay
from app.services.timezone_utils import TASHKENT_TZ

TOUCH_EVERY = timedelta(minutes=5)

# Admin paneldagi holat chegaralari (kun).
ACTIVE_DAYS = 7
RECENT_DAYS = 30


async def touch(session: AsyncSession, user: User, now: datetime | None = None) -> None:
    """Foydalanuvchi hozir faol ekanini belgilaydi (kerak bo'lsagina yozadi)."""
    now = now or datetime.now(UTC)
    last = user.last_seen_at
    if last is not None and now - last < TOUCH_EVERY:
        return
    today = now.astimezone(TASHKENT_TZ).date()
    user.last_seen_at = now
    if last is None or last.astimezone(TASHKENT_TZ).date() != today:
        await session.execute(
            insert(UserActivityDay)
            .values(user_id=user.id, day=today)
            .on_conflict_do_nothing(index_elements=["user_id", "day"])
        )
    await session.commit()
