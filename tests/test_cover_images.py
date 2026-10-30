"""Universitet/grant rasmi: sehrgarda yuklash va Mini App uchun berish."""

import pytest
from fastapi import HTTPException

from app.db.models import Country, University
from app.services.cover_images import apply_cover_upload, cover_url
from app.webapp import api

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


class _Upload:
    def __init__(self, data: bytes, content_type: str = "image/png", filename: str = "uni.png") -> None:
        self._data = data
        self.content_type = content_type
        self.filename = filename

    async def read(self) -> bytes:
        return self._data


async def _university(session) -> University:
    country = Country(name_uz="Germaniya", name_ru="Германия", name_en="Germany", iso_code="DE")
    session.add(country)
    await session.flush()
    university = University(name="TU Munich", city="Munich", country_id=country.id, timezone="Europe/Berlin")
    session.add(university)
    await session.flush()
    return university


async def test_upload_sets_versioned_url_and_endpoint_serves_it(session) -> None:
    university = await _university(session)
    assert cover_url("university", university) is None

    await apply_cover_upload(university, _Upload(PNG), remove=False)
    await session.commit()

    assert cover_url("university", university) == f"/api/webapp/images/university/{university.id}?v=1"
    response = await api.get_cover_image("university", university.id, session)
    assert response.body == PNG
    assert response.media_type == "image/png"
    assert "immutable" in response.headers["cache-control"]

    # Yangi rasm — yangi versiya, ya'ni yangi manzil (eski kesh ishlatilmaydi).
    await apply_cover_upload(university, _Upload(PNG + b"1"), remove=False)
    assert university.cover_version == 2


async def test_no_new_file_keeps_cover_and_remove_clears_it(session) -> None:
    university = await _university(session)
    await apply_cover_upload(university, _Upload(PNG), remove=False)

    await apply_cover_upload(university, _Upload(b"", filename=""), remove=False)
    assert university.cover_version == 1

    await apply_cover_upload(university, None, remove=True)
    await session.commit()
    assert cover_url("university", university) is None
    with pytest.raises(HTTPException):
        await api.get_cover_image("university", university.id, session)


@pytest.mark.parametrize(
    ("upload", "message"),
    [
        (_Upload(PNG, content_type="application/pdf", filename="x.pdf"), "JPG, PNG"),
        (_Upload(b"0" * (3 * 1024 * 1024 + 1)), "3 MB"),
    ],
)
async def test_rejects_wrong_type_and_too_large(session, upload, message) -> None:
    university = await _university(session)

    with pytest.raises(ValueError, match=message):
        await apply_cover_upload(university, upload, remove=False)
    assert university.cover_version == 0


async def test_unknown_kind_is_404(session) -> None:
    with pytest.raises(HTTPException) as exc:
        await api.get_cover_image("user", 1, session)
    assert exc.value.status_code == 404
