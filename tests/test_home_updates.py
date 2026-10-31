"""Bosh sahifa "Yangiliklar": faqat faollari, eng yangisi tepada, 5 tagacha."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HomeUpdate, UpdateKind, User
from app.webapp import api


async def test_lists_active_updates_newest_first(session: AsyncSession) -> None:
    today = date(2027, 3, 10)
    session.add_all(
        [
            HomeUpdate(
                title=f"Yangilik {i}", kind=UpdateKind.NEW, published_on=today - timedelta(days=i)
            )
            for i in range(7)
        ]
        + [HomeUpdate(title="Yashirin", kind=UpdateKind.INFO, published_on=today, is_active=False)]
    )
    user = User(telegram_id=1)
    session.add(user)
    await session.commit()

    items = await api.list_updates(user, session)

    assert [item.title for item in items] == [f"Yangilik {i}" for i in range(5)]
    assert items[0].kind == "new"
    assert items[0].published_on == "2027-03-10"
