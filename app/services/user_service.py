from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Country, User


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    stmt = (
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(
            selectinload(User.target_countries),
            selectinload(User.language_certificates),
            selectinload(User.other_tests),
        )
    )
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is not None:
        if username and user.username != username:
            user.username = username
            await session.commit()
        return user

    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.commit()
    await session.refresh(user, attribute_names=["target_countries", "language_certificates", "other_tests"])
    return user


async def set_target_countries(session: AsyncSession, user: User, country_ids: list[int]) -> None:
    stmt = select(Country).where(Country.id.in_(country_ids))
    countries = (await session.execute(stmt)).scalars().all()
    user.target_countries = list(countries)
    await session.commit()


async def get_user_with_profile(session: AsyncSession, telegram_id: int) -> User | None:
    stmt = (
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(
            selectinload(User.target_countries),
            selectinload(User.language_certificates),
            selectinload(User.other_tests),
        )
    )
    return (await session.execute(stmt)).scalar_one_or_none()
