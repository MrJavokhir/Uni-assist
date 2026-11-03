"""Admission Kit xizmati ikonkasi: admin panelda yuklanadi, Mini App'ga beriladi."""

import pytest
from fastapi import HTTPException

from app.db.models import AdmissionService, ServiceKind
from app.services import kit_service
from app.webapp import api

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


async def _service(session) -> AdmissionService:
    service = AdmissionService(
        code="icon-test", title_uz="Qo'llanma", kind=ServiceKind.FILE, price_currency="UZS"
    )
    session.add(service)
    await session.flush()
    return service


async def test_saved_icon_is_served_and_new_upload_changes_url(session) -> None:
    service = await _service(session)
    assert kit_service.icon_url(service) is None

    kit_service.save_icon(service, "image/png", PNG)
    await session.commit()

    first_url = kit_service.icon_url(service)
    assert first_url == f"/api/webapp/images/service/{service.id}?v=1"
    response = await api.get_cover_image("service", service.id, session)
    assert response.body == PNG
    assert response.media_type == "image/png"

    kit_service.save_icon(service, "image/png", PNG + b"1")
    assert kit_service.icon_url(service) != first_url


async def test_deleted_icon_is_404(session) -> None:
    service = await _service(session)
    kit_service.save_icon(service, "image/png", PNG)
    kit_service.delete_icon(service)
    await session.commit()

    assert kit_service.icon_url(service) is None
    with pytest.raises(HTTPException) as exc:
        await api.get_cover_image("service", service.id, session)
    assert exc.value.status_code == 404


@pytest.mark.parametrize(
    ("content_type", "data", "message"),
    [
        ("image/svg+xml", PNG, "JPG, PNG"),
        ("image/png", b"", "bo'sh"),
        ("image/png", b"0" * (kit_service.MAX_ICON_BYTES + 1), "juda katta"),
    ],
    ids=["svg", "empty", "too-large"],
)
async def test_rejects_bad_files(session, content_type, data, message) -> None:
    service = await _service(session)

    with pytest.raises(kit_service.FileRejected, match=message):
        kit_service.save_icon(service, content_type, data)
    assert not service.icon_version
