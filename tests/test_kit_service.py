"""Admission Kit PDF qo'llanmalari: qabul qilish, qulf va yetkazish.

Diqqat markazida ikki narsa:
  * pul to'lamagan odam faylni OLA OLMASLIGI (`owns`);
  * fayl almashtirilganda Telegram keshi eskirib qolmasligi.
Ikkalasi ham jimgina buziladigan joylar — testsiz sezilmaydi.
"""

from dataclasses import dataclass

import pytest
from sqlalchemy import select

from app.db.models import AdmissionService, ServiceFile, ServiceRequest, User
from app.services import kit_service

PDF = b"%PDF-1.7 soxta qo'llanma"


@dataclass
class _Document:
    file_id: str


@dataclass
class _Sent:
    document: _Document


class FakeBot:
    """Telegram o'rniga: nima yuborilganini yozib boradi."""

    def __init__(self, *, fail_file_ids: bool = False) -> None:
        self.calls: list[object] = []
        self.fail_file_ids = fail_file_ids

    async def send_document(self, chat_id, document, **kwargs):
        if self.fail_file_ids and isinstance(document, str):
            raise RuntimeError("Bad Request: wrong file identifier")
        self.calls.append(document)
        return _Sent(document=_Document(file_id="tg-file-1"))


async def _service(session, title: str = "CV qo'llanmasi") -> AdmissionService:
    service = AdmissionService(code=f"svc-{title}", title_uz=title, price_currency="UZS")
    session.add(service)
    await session.flush()
    return service


async def _user(session, telegram_id: int = 777) -> User:
    user = User(telegram_id=telegram_id, username="tester")
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_rejects_file_that_is_not_pdf(session) -> None:
    """Kengaytmaga ishonib bo'lmaydi: .pdf deb nomlangan rasm ham keladi."""
    service = await _service(session)

    with pytest.raises(kit_service.FileRejected):
        await kit_service.save_file(session, service, "qollanma.pdf", b"PK\x03\x04 zip")

    assert (await session.execute(select(ServiceFile))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_rejects_file_over_limit(session) -> None:
    service = await _service(session)
    too_big = PDF + b"0" * kit_service.MAX_PDF_BYTES

    with pytest.raises(kit_service.FileRejected):
        await kit_service.save_file(session, service, "katta.pdf", too_big)


@pytest.mark.asyncio
async def test_replacing_file_clears_telegram_cache(session) -> None:
    """Eng xavfli xato: fayl almashtirilgan, lekin Telegram ESKI nusxani
    yuborishda davom etadi."""
    service = await _service(session)
    row = await kit_service.save_file(session, service, "v1.pdf", PDF)
    row.telegram_file_id = "eski-id"
    await session.flush()

    updated = await kit_service.save_file(session, service, "v2.pdf", PDF + b" v2")

    assert updated.filename == "v2.pdf"
    assert updated.telegram_file_id is None
    # Bitta xizmatga bitta fayl — yangisi o'rniga yoziladi.
    rows = (await session.execute(select(ServiceFile))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_filename_gets_pdf_extension(session) -> None:
    service = await _service(session)
    row = await kit_service.save_file(session, service, "qollanma", PDF)
    assert row.filename == "qollanma.pdf"


@pytest.mark.asyncio
async def test_owns_is_false_until_purchase(session) -> None:
    service = await _service(session)
    user = await _user(session)

    assert await kit_service.owns(session, user, service.id) is False

    session.add(ServiceRequest(user_id=user.id, service_id=service.id))
    await session.flush()

    assert await kit_service.owns(session, user, service.id) is True


@pytest.mark.asyncio
async def test_first_delivery_uploads_bytes_then_reuses_file_id(session) -> None:
    service = await _service(session)
    user = await _user(session)
    await kit_service.save_file(session, service, "qollanma.pdf", PDF)
    bot = FakeBot()

    await kit_service.deliver_file(session, bot, user, service)
    # Birinchi marta baytlar ketadi.
    assert not isinstance(bot.calls[0], str)

    await kit_service.deliver_file(session, bot, user, service)
    # Ikkinchi marta keshlangan id — megabaytlar qayta jo'natilmaydi.
    assert bot.calls[1] == "tg-file-1"


@pytest.mark.asyncio
async def test_delivery_falls_back_to_bytes_when_cached_id_fails(session) -> None:
    """Telegram'dagi nusxa yo'qolsa ham foydalanuvchi faylsiz qolmasligi kerak."""
    service = await _service(session)
    user = await _user(session)
    row = await kit_service.save_file(session, service, "qollanma.pdf", PDF)
    row.telegram_file_id = "yaroqsiz-id"
    await session.flush()
    bot = FakeBot(fail_file_ids=True)

    await kit_service.deliver_file(session, bot, user, service)

    assert len(bot.calls) == 1
    assert not isinstance(bot.calls[0], str)
    assert row.telegram_file_id == "tg-file-1"


@pytest.mark.asyncio
async def test_delivery_without_file_returns_none(session) -> None:
    """PDF biriktirilmagan xizmat — bu qo'lda bajariladigan xizmat."""
    service = await _service(session)
    user = await _user(session)

    assert await kit_service.deliver_file(session, FakeBot(), user, service) is None


@pytest.mark.asyncio
async def test_file_is_reachable_after_plain_get(session) -> None:
    """`session.get()` bilan olingan xizmatda ham `.file` o'qilishi kerak.

    Sotib olish endpointi xizmatni aynan shunday oladi va darhol
    `service.file is not None` deb so'raydi. Bog'lanish yuklanmagan bo'lsa,
    async sessiyada bu xato bilan yiqilardi.
    """
    service = await _service(session)
    await kit_service.save_file(session, service, "qollanma.pdf", PDF)
    await session.commit()
    session.expunge_all()

    fresh = await session.get(AdmissionService, service.id)
    assert fresh.file is not None
    assert fresh.file.filename == "qollanma.pdf"
