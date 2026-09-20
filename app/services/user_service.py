from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Country, LanguageCertType, UiLanguage, User, UserLanguageCertificate

_PROFILE_RELATIONSHIPS = ("target_countries", "language_certificates", "other_tests", "saved_programs")


def _language_from_telegram(code: str | None) -> UiLanguage:
    """Telegram interfeys tilidan boshlang'ich til.

    Yangi foydalanuvchining `ui_language`i doim "uz" bo'lib qolardi va Mini App
    bot orqali emas, to'g'ridan-to'g'ri ochilganda ruszabon foydalanuvchi ham
    o'zbekcha ko'rardi. Botda til so'raladi va uni ustiga yozadi — bu faqat
    oqilona boshlang'ich qiymat.
    """
    base = (code or "").split("-")[0].lower()
    try:
        return UiLanguage(base)
    except ValueError:
        return UiLanguage.UZ


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    language_code: str | None = None,
) -> User:
    stmt = (
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(*(selectinload(getattr(User, rel)) for rel in _PROFILE_RELATIONSHIPS))
    )
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is not None:
        if username and user.username != username:
            user.username = username
            await session.commit()
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        ui_language=_language_from_telegram(language_code),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user, attribute_names=list(_PROFILE_RELATIONSHIPS))
    return user


async def set_target_countries(session: AsyncSession, user: User, country_ids: list[int]) -> None:
    stmt = select(Country).where(Country.id.in_(country_ids))
    countries = (await session.execute(stmt)).scalars().all()
    user.target_countries = list(countries)
    await session.commit()


async def upsert_language_certificate(
    session: AsyncSession, user: User, cert_type: LanguageCertType, score: float
) -> None:
    stmt = select(UserLanguageCertificate).where(
        UserLanguageCertificate.user_id == user.id, UserLanguageCertificate.type == cert_type
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        existing.score = score
    else:
        session.add(
            UserLanguageCertificate(
                user_id=user.id, type=cert_type, score=score, exam_date=datetime.now(UTC).date()
            )
        )
    await session.commit()


async def get_user_with_profile(session: AsyncSession, telegram_id: int) -> User | None:
    stmt = (
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(*(selectinload(getattr(User, rel)) for rel in _PROFILE_RELATIONSHIPS))
    )
    return (await session.execute(stmt)).scalar_one_or_none()
