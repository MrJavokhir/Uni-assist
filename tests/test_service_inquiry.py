"""Admission Kit: qo'lda bajariladigan xizmatga forma orqali so'rov.

Mentor sessiya va to'liq yordam endi vaqt tanlamaydi va pul yechmaydi —
davlat va mavzular bilan so'rov bot orqali adminlarga keladi.
"""

from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.db.models import AdmissionService, Country, ServiceKind, User
from app.webapp import api
from app.webapp.schemas import ServiceInquiryIn


@pytest.fixture
def sent(monkeypatch):
    messages: list[str] = []

    async def fake_notify(session, html: str) -> bool:
        messages.append(html)
        return True

    monkeypatch.setattr(api, "_notify_admins", fake_notify)
    return messages


async def _setup(session, kind=ServiceKind.REQUEST):
    service = AdmissionService(code=f"svc-{kind.value}", title_uz="1-on-1 mentor sessiya", kind=kind)
    country = Country(name_uz="Germaniya", name_ru="Германия", name_en="Germany", iso_code="DE")
    user = User(telegram_id=777, username="aziz", balance=Decimal(50000))
    session.add_all([service, country, user])
    await session.flush()
    return service, country, user


async def test_inquiry_reaches_admins_with_details_and_no_charge(session, sent) -> None:
    service, country, user = await _setup(session)

    result = await api.send_service_inquiry(
        service.id,
        ServiceInquiryIn(country_id=country.id, topics=["documents", "visa", "bogus"], text="IELTS 6.5 bor"),
        user,
        session,
    )

    assert result == {"sent": True}
    html = sent[0]
    assert "1-on-1 mentor sessiya" in html
    assert "Germaniya" in html
    assert "Hujjatlar, Viza" in html  # noma'lum kalit tashlab yuboriladi
    assert "IELTS 6.5 bor" in html
    assert 'href="tg://user?id=777"' in html
    await session.refresh(user)
    assert Decimal(str(user.balance)) == Decimal(50000), "pul yechilmasligi kerak"


async def test_inquiry_without_country_says_not_sure(session, sent) -> None:
    service, _, user = await _setup(session)

    await api.send_service_inquiry(service.id, ServiceInquiryIn(topics=["other"]), user, session)

    assert "Hali aniq emas" in sent[0]


async def test_guide_service_does_not_accept_inquiry(session, sent) -> None:
    service, _, user = await _setup(session, kind=ServiceKind.FILE)

    with pytest.raises(HTTPException) as exc:
        await api.send_service_inquiry(service.id, ServiceInquiryIn(topics=["other"]), user, session)

    assert exc.value.status_code == 404
    assert sent == []
