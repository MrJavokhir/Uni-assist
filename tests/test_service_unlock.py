"""Admission Kit xizmatini do'st taklif qilib ochish.

Pulga tegishli qaror, shuning uchun diqqat markazida: yetarli taklifi
bo'lmagan odamdan pul olinishi, yetarlisi bo'lgandan OLINMASLIGI va
chegaraning aniq ishlashi.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select, update

from app.db.models import (
    AdmissionService,
    BalanceTransaction,
    ServiceKind,
    ServiceRequest,
    User,
)
from app.webapp.api import request_service


async def _setup(
    session,
    *,
    price: Decimal | None,
    unlock_invites: int,
    confirmed: int = 0,
    unconfirmed: int = 0,
    balance: Decimal = Decimal(0),
) -> tuple[AdmissionService, User]:
    """Xizmat, xaridor va uning takliflari.

    Oxirida COMMIT va `expunge_all()` SHART: `request_service()` xizmatni
    `session.get()` bilan oladi, sessiyada turgan obyekt uchun esa u
    so'rov yubormaydi va `service.file` bog'lanishi yuklanmay qoladi —
    unga murojaat qilinganda async sessiya "MissingGreenlet" beradi.
    Haqiqiy so'rovda bog'lanish selectin bilan birga keladi.
    """
    code = f"svc-{unlock_invites}-{price}-{confirmed}-{unconfirmed}"
    service = AdmissionService(
        code=code,
        title_uz="Mentor",
        kind=ServiceKind.REQUEST,
        price_amount=price,
        price_currency="UZS",
        unlock_invites=unlock_invites,
    )
    buyer = User(telegram_id=900, username="buyer", balance=balance)
    session.add_all([service, buyer])
    await session.flush()

    telegram_id = 901
    for _ in range(confirmed):
        session.add(User(telegram_id=telegram_id, referred_by_id=buyer.id, referral_confirmed=True))
        telegram_id += 1
    for _ in range(unconfirmed):
        session.add(
            User(telegram_id=telegram_id, referred_by_id=buyer.id, referral_confirmed=False)
        )
        telegram_id += 1

    await session.commit()
    session.expunge_all()

    service = (
        await session.execute(select(AdmissionService).where(AdmissionService.code == code))
    ).scalar_one()
    buyer = (await session.execute(select(User).where(User.telegram_id == 900))).scalar_one()
    return service, buyer


async def _transactions(session, user: User) -> list[BalanceTransaction]:
    rows = await session.execute(
        select(BalanceTransaction).where(BalanceTransaction.user_id == user.id)
    )
    return list(rows.scalars().all())


@pytest.mark.asyncio
async def test_enough_invites_unlocks_without_charging(session) -> None:
    service, buyer = await _setup(
        session, price=Decimal(50000), unlock_invites=3, confirmed=3, balance=Decimal(50000)
    )

    result = await request_service(service.id, payload=None, user=buyer, session=session)

    assert result.unlocked_by_invites is True
    assert result.charged is None
    assert Decimal(str(buyer.balance)) == Decimal(50000), "pul yechilmasligi kerak"
    assert await _transactions(session, buyer) == []

    saved = (await session.execute(select(ServiceRequest))).scalar_one()
    assert saved.unlocked_by_invites is True


@pytest.mark.asyncio
async def test_not_enough_invites_still_charges(session) -> None:
    service, buyer = await _setup(
        session, price=Decimal(50000), unlock_invites=3, confirmed=2, balance=Decimal(50000)
    )

    result = await request_service(service.id, payload=None, user=buyer, session=session)

    assert result.unlocked_by_invites is False
    assert result.charged == 50000
    assert Decimal(str(buyer.balance)) == Decimal(0)

    saved = (await session.execute(select(ServiceRequest))).scalar_one()
    assert saved.unlocked_by_invites is False


@pytest.mark.asyncio
async def test_unconfirmed_invites_do_not_count(session) -> None:
    """Havolani bosib ketgan odam xizmat ochmaydi.

    Aks holda soxta akkaunt bilan /start bosish yetarli bo'lib qolardi.
    """
    service, buyer = await _setup(
        session,
        price=Decimal(50000),
        unlock_invites=2,
        confirmed=1,
        unconfirmed=1,
        balance=Decimal(50000),
    )

    result = await request_service(service.id, payload=None, user=buyer, session=session)

    assert result.unlocked_by_invites is False
    assert Decimal(str(buyer.balance)) == Decimal(0)


@pytest.mark.asyncio
async def test_exact_threshold_unlocks(session) -> None:
    """Chegara aynan tengda ham ishlashi kerak (">=", ">" emas)."""
    service, buyer = await _setup(
        session, price=Decimal(10000), unlock_invites=2, confirmed=2, balance=Decimal(10000)
    )

    result = await request_service(service.id, payload=None, user=buyer, session=session)

    assert result.unlocked_by_invites is True
    assert Decimal(str(buyer.balance)) == Decimal(10000)


@pytest.mark.asyncio
async def test_zero_setting_means_money_only(session) -> None:
    """0 — bunday imkoniyat yo'q, takliflari ko'p bo'lsa ham pulga."""
    service, buyer = await _setup(
        session, price=Decimal(10000), unlock_invites=0, confirmed=4, balance=Decimal(10000)
    )

    result = await request_service(service.id, payload=None, user=buyer, session=session)

    assert result.unlocked_by_invites is False
    assert Decimal(str(buyer.balance)) == Decimal(0)


@pytest.mark.asyncio
async def test_unlock_works_without_balance(session) -> None:
    """Asosiy holat: puli yo'q, lekin do'st taklif qilgan odam."""
    service, buyer = await _setup(
        session, price=Decimal(50000), unlock_invites=1, confirmed=1, balance=Decimal(0)
    )

    result = await request_service(service.id, payload=None, user=buyer, session=session)

    assert result.unlocked_by_invites is True
    assert Decimal(str(buyer.balance)) == Decimal(0)


async def _old_friends_then_service(
    session, *, count_from_none: bool
) -> tuple[AdmissionService, User]:
    """Do'stlar AVVAL keladi (alohida tranzaksiya), qo'llanma KEYIN qo'shiladi."""
    buyer = User(telegram_id=950, username="old", balance=Decimal(20000))
    session.add(buyer)
    await session.flush()
    session.add_all(
        User(telegram_id=951 + i, referred_by_id=buyer.id, referral_confirmed=True)
        for i in range(3)
    )
    await session.commit()

    service = AdmissionService(
        code=f"new-guide-{count_from_none}",
        title_uz="Yangi qo'llanma",
        kind=ServiceKind.REQUEST,
        price_amount=Decimal(10000),
        price_currency="UZS",
        unlock_invites=3,
    )
    session.add(service)
    await session.commit()
    if count_from_none:
        # Migratsiyadan oldingi xizmatlar kabi (server_default'ni chetlab o'tadi).
        await session.execute(
            update(AdmissionService)
            .where(AdmissionService.id == service.id)
            .values(invites_count_from=None)
        )
        await session.commit()
    session.expunge_all()
    service = (
        await session.execute(select(AdmissionService).where(AdmissionService.code == service.code))
    ).scalar_one()
    buyer = (await session.execute(select(User).where(User.telegram_id == 950))).scalar_one()
    return service, buyer


@pytest.mark.asyncio
async def test_old_invites_do_not_unlock_new_guide(session) -> None:
    service, buyer = await _old_friends_then_service(session, count_from_none=False)

    result = await request_service(service.id, payload=None, user=buyer, session=session)

    assert result.unlocked_by_invites is False
    assert result.charged is not None


@pytest.mark.asyncio
async def test_empty_start_date_also_ignores_older_invites(session) -> None:
    """Sanasi bo'sh xizmat ham: undan oldin kelgan do'stlar sanalmaydi."""
    service, buyer = await _old_friends_then_service(session, count_from_none=True)

    result = await request_service(service.id, payload=None, user=buyer, session=session)

    assert result.unlocked_by_invites is False


@pytest.mark.asyncio
async def test_used_invites_do_not_unlock_next_service(session) -> None:
    buyer = User(telegram_id=970, username="free", balance=Decimal(20000))
    first = AdmissionService(
        code="free-a",
        title_uz="A",
        kind=ServiceKind.REQUEST,
        price_amount=Decimal(10000),
        price_currency="UZS",
        unlock_invites=2,
    )
    second = AdmissionService(
        code="free-b",
        title_uz="B",
        kind=ServiceKind.REQUEST,
        price_amount=Decimal(10000),
        price_currency="UZS",
        unlock_invites=2,
    )
    session.add_all([buyer, first, second])
    await session.flush()
    session.add_all(
        User(telegram_id=971 + i, referred_by_id=buyer.id, referral_confirmed=True)
        for i in range(2)
    )
    await session.commit()
    first_id, second_id = first.id, second.id
    session.expunge_all()
    buyer = (await session.execute(select(User).where(User.telegram_id == 970))).scalar_one()

    opened = await request_service(first_id, payload=None, user=buyer, session=session)
    assert opened.unlocked_by_invites is True

    # O'sha ikki do'st ikkinchi xizmatga o'tmaydi — pul yechiladi.
    charged = await request_service(second_id, payload=None, user=buyer, session=session)
    assert charged.unlocked_by_invites is False
    assert charged.charged is not None


@pytest.mark.asyncio
async def test_fresh_friends_unlock_next_service(session) -> None:
    buyer = User(telegram_id=980, username="again", balance=Decimal(0))
    first = AdmissionService(
        code="next-a",
        title_uz="A",
        kind=ServiceKind.REQUEST,
        price_amount=Decimal(10000),
        price_currency="UZS",
        unlock_invites=1,
    )
    second = AdmissionService(
        code="next-b",
        title_uz="B",
        kind=ServiceKind.REQUEST,
        price_amount=Decimal(10000),
        price_currency="UZS",
        unlock_invites=1,
    )
    session.add_all([buyer, first, second])
    await session.flush()
    session.add(User(telegram_id=981, referred_by_id=buyer.id, referral_confirmed=True))
    await session.commit()
    first_id, second_id, buyer_id = first.id, second.id, buyer.id
    session.expunge_all()
    buyer = (await session.execute(select(User).where(User.telegram_id == 980))).scalar_one()
    assert (
        await request_service(first_id, payload=None, user=buyer, session=session)
    ).unlocked_by_invites

    session.add(User(telegram_id=982, referred_by_id=buyer_id, referral_confirmed=True))
    await session.commit()

    result = await request_service(second_id, payload=None, user=buyer, session=session)
    assert result.unlocked_by_invites is True
