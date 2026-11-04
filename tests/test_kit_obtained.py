"""Admission Kit: olingan xizmatlar pulga, do'st taklifi bilan yoki bepul."""

from decimal import Decimal

from app.db.models import AdmissionService, ServiceKind, ServiceRequest, User
from app.services import kit_service, payment_service
from app.services.kit_service import OBTAINED_FREE, OBTAINED_INVITES, OBTAINED_PAID


async def _seed(session) -> tuple[AdmissionService, AdmissionService]:
    guide = AdmissionService(
        code="obt-guide", title_uz="Guide", kind=ServiceKind.FILE,
        price_amount=Decimal(10000), price_currency="UZS",
    )
    helper = AdmissionService(
        code="obt-help", title_uz="Help", kind=ServiceKind.REQUEST, price_currency="UZS"
    )
    buyer = User(telegram_id=9001, username="buyer", balance=Decimal(50000))
    inviter = User(telegram_id=9002, username="inviter")
    asker = User(telegram_id=9003, username="asker")
    session.add_all([guide, helper, buyer, inviter, asker])
    await session.flush()

    await payment_service.charge_service(session, buyer, guide)
    session.add_all(
        [
            ServiceRequest(user_id=buyer.id, service_id=guide.id),
            ServiceRequest(user_id=inviter.id, service_id=guide.id, unlocked_by_invites=True),
            ServiceRequest(user_id=asker.id, service_id=helper.id),
        ]
    )
    await session.commit()
    return guide, helper


async def test_counts_split_by_how_obtained(session) -> None:
    guide, helper = await _seed(session)

    counts = await kit_service.obtained_counts(session)

    assert counts == {
        guide.id: {OBTAINED_PAID: 1, OBTAINED_INVITES: 1},
        helper.id: {OBTAINED_FREE: 1},
    }


async def test_list_includes_invited_and_shows_real_amount(session) -> None:
    await _seed(session)

    rows = await kit_service.obtained_rows(session)

    got = {row.request.user.username: (row.how, row.paid) for row in rows}
    assert got == {
        "buyer": (OBTAINED_PAID, Decimal(10000)),
        "inviter": (OBTAINED_INVITES, None),
        "asker": (OBTAINED_FREE, None),
    }


async def test_filters_by_how_and_kind(session) -> None:
    await _seed(session)

    invited = await kit_service.obtained_rows(session, how=OBTAINED_INVITES)
    manual = await kit_service.obtained_rows(session, kind=ServiceKind.REQUEST)

    assert [row.request.user.username for row in invited] == ["inviter"]
    assert [row.request.user.username for row in manual] == ["asker"]


async def test_label_ignores_later_price_change(session) -> None:
    """Bepul olingan xizmatga keyin narx qo'yilsa, olgan odam "sotib olgan" bo'lmaydi."""
    _, helper = await _seed(session)
    helper.price_amount = Decimal(5000)
    await session.commit()

    rows = await kit_service.obtained_rows(session, kind=ServiceKind.REQUEST)

    assert (rows[0].how, rows[0].paid) == (OBTAINED_FREE, None)
