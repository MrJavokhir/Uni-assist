"""Uchrashuv vaqtlari: bo'sh oynalar va band qilish.

Eng muhim talab — bitta oyna ikki kishiga berilmasligi. Ikki odam bir
vaqtda bosgan holat testda shartli UPDATE orqali tekshiriladi: ikkinchi
urinish qator o'zgartira olmasligi kerak.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.models import AdmissionService, ServiceRequest, ServiceSlot, User
from app.services import booking_service


async def _service(session, code: str = "mentor") -> AdmissionService:
    service = AdmissionService(
        code=code, title_uz="Mentor", price_currency="UZS", requires_booking=True
    )
    session.add(service)
    await session.flush()
    return service


async def _request(session, service: AdmissionService, telegram_id: int) -> ServiceRequest:
    user = User(telegram_id=telegram_id, username=f"u{telegram_id}")
    session.add(user)
    await session.flush()
    row = ServiceRequest(user_id=user.id, service_id=service.id)
    session.add(row)
    await session.flush()
    return row


def _soon(hours: int = 24) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours)


@pytest.mark.asyncio
async def test_free_slots_skips_past_and_booked(session) -> None:
    service = await _service(session)
    future = await booking_service.add_slot(session, service.id, _soon(24))
    await booking_service.add_slot(session, service.id, datetime.now(UTC) - timedelta(hours=1))
    taken = await booking_service.add_slot(session, service.id, _soon(48))
    request = await _request(session, service, 101)
    await booking_service.claim(session, taken.id, service.id, request.id)

    free = await booking_service.free_slots(session, service.id)

    assert [s.id for s in free] == [future.id]


@pytest.mark.asyncio
async def test_slot_cannot_be_taken_twice(session) -> None:
    """Ikki odam bir vaqtda bosgan holat."""
    service = await _service(session)
    slot = await booking_service.add_slot(session, service.id, _soon())
    first = await _request(session, service, 201)
    second = await _request(session, service, 202)

    await booking_service.claim(session, slot.id, service.id, first.id)

    with pytest.raises(booking_service.SlotTaken):
        await booking_service.claim(session, slot.id, service.id, second.id)

    assert (await session.get(ServiceSlot, slot.id)).request_id == first.id


@pytest.mark.asyncio
async def test_slot_of_another_service_is_refused(session) -> None:
    """Boshqa xizmatning oynasini band qilib bo'lmaydi."""
    mentor = await _service(session, "mentor")
    other = await _service(session, "other")
    slot = await booking_service.add_slot(session, other.id, _soon())
    request = await _request(session, mentor, 301)

    with pytest.raises(booking_service.SlotTaken):
        await booking_service.claim(session, slot.id, mentor.id, request.id)


@pytest.mark.asyncio
async def test_past_slot_cannot_be_claimed(session) -> None:
    service = await _service(session)
    slot = await booking_service.add_slot(
        session, service.id, datetime.now(UTC) - timedelta(minutes=5)
    )
    request = await _request(session, service, 401)

    with pytest.raises(booking_service.SlotTaken):
        await booking_service.claim(session, slot.id, service.id, request.id)


@pytest.mark.asyncio
async def test_booked_slot_is_not_deleted(session) -> None:
    """Odam pul to'lab o'sha vaqtga yozilgan — oyna yo'qolmasligi kerak."""
    service = await _service(session)
    slot = await booking_service.add_slot(session, service.id, _soon())
    request = await _request(session, service, 501)
    await booking_service.claim(session, slot.id, service.id, request.id)

    assert await booking_service.delete_slot(session, slot.id) is False
    assert await session.get(ServiceSlot, slot.id) is not None


@pytest.mark.asyncio
async def test_free_slot_is_deleted(session) -> None:
    service = await _service(session)
    slot = await booking_service.add_slot(session, service.id, _soon())

    assert await booking_service.delete_slot(session, slot.id) is True
    assert (await session.execute(select(ServiceSlot))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_free_counts_groups_by_service(session) -> None:
    mentor = await _service(session, "mentor")
    other = await _service(session, "other")
    await booking_service.add_slot(session, mentor.id, _soon(24))
    await booking_service.add_slot(session, mentor.id, _soon(48))
    await booking_service.add_slot(session, other.id, _soon(24))

    counts = await booking_service.free_counts(session)

    assert counts[mentor.id] == 2
    assert counts[other.id] == 1


@pytest.mark.asyncio
async def test_labels_use_tashkent_time(session) -> None:
    """Vaqt serverning mintaqasiga emas, Toshkentga bog'langan bo'lishi kerak."""
    service = await _service(session)
    # 2026-10-05 09:00 UTC = 14:00 Toshkent, dushanba.
    slot = await booking_service.add_slot(
        session, service.id, datetime(2026, 10, 5, 9, 0, tzinfo=UTC)
    )

    date_label, time_label = booking_service.labels(slot, "uz")

    assert time_label == "14:00"
    assert date_label == "05.10.2026, dushanba"
    assert booking_service.labels(slot, "en")[0].endswith("Monday")
