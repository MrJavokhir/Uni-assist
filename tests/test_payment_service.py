"""Balans mantig'i — pul bilan ishlaydigan qism.

Asosiy talab: qoldiq (`users.balance`) va tarix (`balance_transactions`)
doim bir-biriga mos bo'lsin. Shuning uchun har bir testda qoldiq ham,
oxirgi tranzaksiyaning `balance_after` qiymati ham tekshiriladi.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import (
    AdmissionService,
    BalanceTransaction,
    PaymentStatus,
    TransactionKind,
    User,
)
from app.services.payment_service import (
    InsufficientBalance,
    approve_payment,
    charge_service,
    get_settings,
    latest_open_payment,
    start_topup,
)


async def _user(session, telegram_id: int = 555) -> User:
    user = User(telegram_id=telegram_id, username="tester")
    session.add(user)
    await session.flush()
    return user


async def _service(session, price: Decimal | None) -> AdmissionService:
    service = AdmissionService(
        code=f"svc{price or 0}",
        title_uz="Mentor",
        price_amount=price,
        price_currency="UZS",
    )
    session.add(service)
    await session.flush()
    return service


async def _last_transaction(session, user: User) -> BalanceTransaction:
    stmt = (
        select(BalanceTransaction)
        .where(BalanceTransaction.user_id == user.id)
        .order_by(BalanceTransaction.id.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one()


@pytest.mark.asyncio
async def test_approve_credits_balance_and_writes_history(session) -> None:
    user = await _user(session)
    payment = await start_topup(session, user, Decimal(25000))

    balance = await approve_payment(session, payment, admin_telegram_id=1)

    assert balance == Decimal(25000)
    assert Decimal(str(user.balance)) == Decimal(25000)
    assert payment.status == PaymentStatus.APPROVED
    assert payment.reviewed_by == 1

    transaction = await _last_transaction(session, user)
    assert transaction.kind == TransactionKind.TOPUP
    assert Decimal(str(transaction.amount)) == Decimal(25000)
    # Tarix qoldiq bilan mos bo'lishi shart.
    assert Decimal(str(transaction.balance_after)) == Decimal(str(user.balance))


@pytest.mark.asyncio
async def test_approve_twice_does_not_double_credit(session) -> None:
    """Admin bir xil chekni ikki marta tasdiqlab yuborishi mumkin."""
    user = await _user(session)
    payment = await start_topup(session, user, Decimal(10000))

    await approve_payment(session, payment, admin_telegram_id=1)
    await approve_payment(session, payment, admin_telegram_id=1)

    assert Decimal(str(user.balance)) == Decimal(10000)
    rows = (
        await session.execute(
            select(BalanceTransaction).where(BalanceTransaction.user_id == user.id)
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_charge_service_deducts(session) -> None:
    user = await _user(session)
    payment = await start_topup(session, user, Decimal(50000))
    await approve_payment(session, payment, admin_telegram_id=1)

    service = await _service(session, Decimal(30000))
    balance = await charge_service(session, user, service)

    assert balance == Decimal(20000)
    assert Decimal(str(user.balance)) == Decimal(20000)

    transaction = await _last_transaction(session, user)
    assert transaction.kind == TransactionKind.SERVICE
    # Yechish MANFIY yoziladi.
    assert Decimal(str(transaction.amount)) == Decimal(-30000)
    assert transaction.service_id == service.id


@pytest.mark.asyncio
async def test_charge_service_refuses_when_balance_is_short(session) -> None:
    user = await _user(session)
    service = await _service(session, Decimal(30000))

    with pytest.raises(InsufficientBalance):
        await charge_service(session, user, service)

    assert Decimal(str(user.balance or 0)) == Decimal(0)
    rows = (
        await session.execute(
            select(BalanceTransaction).where(BalanceTransaction.user_id == user.id)
        )
    ).scalars().all()
    # Muvaffaqiyatsiz urinish tarixga yozilmasligi kerak.
    assert rows == []


@pytest.mark.asyncio
async def test_service_without_price_is_free(session) -> None:
    """Narxi ko'rsatilmagan xizmat "kelishiladi" degani — summani taxmin
    qilib yechib bo'lmaydi."""
    user = await _user(session)
    service = await _service(session, None)

    balance = await charge_service(session, user, service)

    assert balance == Decimal(0)
    rows = (
        await session.execute(
            select(BalanceTransaction).where(BalanceTransaction.user_id == user.id)
        )
    ).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_settings_row_is_created_when_missing(session) -> None:
    row = await get_settings(session)
    assert row.currency == "UZS"
    assert Decimal(str(row.min_amount)) > 0


@pytest.mark.asyncio
async def test_latest_open_payment_ignores_closed_ones(session) -> None:
    user = await _user(session)
    first = await start_topup(session, user, Decimal(10000))
    await approve_payment(session, first, admin_telegram_id=1)
    second = await start_topup(session, user, Decimal(20000))

    found = await latest_open_payment(session, user)

    assert found is not None
    assert found.id == second.id
