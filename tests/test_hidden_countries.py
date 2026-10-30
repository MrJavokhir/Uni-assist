"""Yashirin davlatlar: yo'nalish sifatida tanlanmaydi, grantlar filtrida qoladi."""

from app.db.models import Country, User
from app.services.user_service import set_target_countries
from app.webapp import api


async def _countries(session) -> tuple[Country, Country]:
    germany = Country(name_uz="Germaniya", name_ru="Германия", name_en="Germany", iso_code="DE")
    brunei = Country(
        name_uz="Bruney", name_ru="Бруней", name_en="Brunei", iso_code="BN", hidden=True
    )
    session.add_all([germany, brunei])
    await session.flush()
    return germany, brunei


async def test_list_marks_hidden_countries(session) -> None:
    await _countries(session)

    countries = await api.list_countries(session)

    assert {c.iso_code: c.hidden for c in countries} == {"DE": False, "BN": True}


async def test_hidden_country_cannot_be_a_target(session) -> None:
    germany, brunei = await _countries(session)
    user = User(telegram_id=1)
    session.add(user)
    await session.flush()
    await session.refresh(user, attribute_names=["target_countries"])

    await set_target_countries(session, user, [germany.id, brunei.id])

    assert [c.iso_code for c in user.target_countries] == ["DE"]
