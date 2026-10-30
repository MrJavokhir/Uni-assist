"""Universitet/grant rasmi: havola sifatida kiritiladi, eski yuklanganlari ham beriladi."""

import pytest
from fastapi import HTTPException
from starlette.datastructures import FormData

from app.admin.wizards import _cover_url_error
from app.db.models import Country, University
from app.webapp import api

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


async def _university(session, **values) -> University:
    country = Country(name_uz="Germaniya", name_ru="Германия", name_en="Germany", iso_code="DE")
    session.add(country)
    await session.flush()
    university = University(
        name="TU Munich", city="Munich", country_id=country.id, timezone="Europe/Berlin", **values
    )
    session.add(university)
    await session.flush()
    return university


async def test_previously_uploaded_cover_is_still_served(session) -> None:
    university = await _university(session, cover_data=PNG, cover_type="image/png")
    await session.commit()

    response = await api.get_cover_image("university", university.id, session)

    assert response.body == PNG
    assert response.media_type == "image/png"
    assert "immutable" in response.headers["cache-control"]


async def test_missing_cover_and_unknown_kind_are_404(session) -> None:
    university = await _university(session)
    await session.commit()

    for kind, item_id in (("university", university.id), ("user", 1)):
        with pytest.raises(HTTPException) as exc:
            await api.get_cover_image(kind, item_id, session)
        assert exc.value.status_code == 404


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("", True),
        ("https://example.com/campus.jpg", True),
        ("/api/webapp/images/university/3?v=1", True),
        ("example.com/campus.jpg", False),
    ],
)
def test_cover_url_validation(url, ok) -> None:
    assert (_cover_url_error(FormData({"cover_url": url})) is None) is ok
