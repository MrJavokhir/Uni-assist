"""«Filtrni tozalash» haqiqatan hamma narsani tozalaydimi.

Bu yerda tekshiriladigan narsa — maydonlar ro'yxati emas, NATIJA: tozalashdan
keyin qidiruvni chegaralaydigan hech narsa qolmasligi kerak. Shu sababli
yangi filtr maydoni qo'shilib, tozalashga qo'shilmasa, test yiqiladi.

Aynan shunday bo'lgandi: o'qish tili qo'shilganda tozalashga tushmay qolgan
va foydalanuvchi "Filtrni tozalash" bosgandan keyin ham ilova filtr qo'yilgan
holatda qolaverardi — "profilni to'ldiring" taklifi boshqa chiqmasdi.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import (
    Country,
    DegreeLevel,
    Field,
    GpaScale,
    LanguageCertType,
    UniversityRankRange,
    User,
    UserLanguageCertificate,
)
from app.webapp.api import RESETTABLE_FILTER_FIELDS, reset_me


async def _filled_user(session) -> User:
    """Filtrning HAMMA maydoni to'ldirilgan foydalanuvchi."""
    country = Country(name_uz="Germaniya", name_ru="Германия", name_en="Germany", iso_code="DE")
    field = Field(code="cs_it", name_uz="IT", name_ru="IT", name_en="IT")
    session.add_all([country, field])
    await session.flush()

    user = User(
        telegram_id=555,
        degree_level=DegreeLevel.MASTER,
        field_id=field.id,
        gpa_raw=Decimal(85),
        gpa_scale=GpaScale.SCALE_100,
        university_rank_range=UniversityRankRange.TOP_300,
        application_fee_ok=True,
        study_language="German",
    )
    user.target_countries = [country]
    session.add(user)
    await session.flush()

    session.add(
        UserLanguageCertificate(
            user_id=user.id,
            type=LanguageCertType.IELTS,
            score=7,
            exam_date=datetime.now(UTC).date(),
        )
    )
    await session.commit()
    await session.refresh(user, attribute_names=["target_countries", "language_certificates"])
    return user


@pytest.mark.asyncio
async def test_reset_leaves_no_filter_behind(session) -> None:
    user = await _filled_user(session)

    await reset_me(user=user, session=session)

    # Qidiruvni chegaralaydigan hech narsa qolmasligi kerak.
    for field_name in RESETTABLE_FILTER_FIELDS:
        assert getattr(user, field_name) is None, field_name
    assert user.target_countries == []
    assert user.language_certificates == []


@pytest.mark.asyncio
async def test_reset_clears_study_language(session) -> None:
    """Aynan shu maydon tozalashdan tushib qolgandi."""
    user = await _filled_user(session)
    assert user.study_language == "German"

    await reset_me(user=user, session=session)

    assert user.study_language is None


@pytest.mark.asyncio
async def test_reset_keeps_language_and_balance(session) -> None:
    """Tozalash profilga tegadi, hisob va interfeys tiliga emas."""
    user = await _filled_user(session)
    user.balance = Decimal(5000)
    await session.commit()
    before_language = user.ui_language

    await reset_me(user=user, session=session)

    assert user.ui_language == before_language
    assert Decimal(str(user.balance)) == Decimal(5000)


@pytest.mark.asyncio
async def test_reset_is_persisted(session) -> None:
    """Tozalash bazaga yozilishi kerak, faqat xotirada qolmasligi."""
    user = await _filled_user(session)

    await reset_me(user=user, session=session)
    session.expunge_all()

    fresh = (await session.execute(select(User).where(User.telegram_id == 555))).scalar_one()
    assert fresh.study_language is None
    assert fresh.degree_level is None
