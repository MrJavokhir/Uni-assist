"""Taklif dasturi: bog'lash, mukofot va suiiste'molga qarshi to'siqlar.

Pul bilan bog'liq, shuning uchun diqqat markazida: mukofot BIR MARTA
berilishi, o'zini o'zi taklif qilib bo'lmasligi va mukofot obunadan
keyin berilishi (darhol emas).
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import BalanceTransaction, TransactionKind, User
from app.services import payment_service, referral_service


async def _user(session, telegram_id: int, username: str | None = None) -> User:
    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.flush()
    return user


async def _bonus(session, amount: Decimal) -> None:
    row = await payment_service.get_settings(session)
    row.referral_bonus = amount
    await session.flush()


def test_payload_parsing() -> None:
    assert referral_service.parse_payload("ref12345") == 12345
    assert referral_service.parse_payload("  ref777  ") == 777
    # Noto'g'ri yoki bo'sh payload jim o'tkazib yuboriladi.
    assert referral_service.parse_payload(None) is None
    assert referral_service.parse_payload("") is None
    assert referral_service.parse_payload("ref") is None
    assert referral_service.parse_payload("hello") is None
    assert referral_service.parse_payload("ref12a") is None


def test_link_needs_bot_username() -> None:
    assert referral_service.build_link(None, 5) is None
    assert referral_service.build_link("uni_bot", 5) == "https://t.me/uni_bot?start=ref5"


@pytest.mark.asyncio
async def test_reward_is_paid_after_subscription(session) -> None:
    await _bonus(session, Decimal(1000))
    inviter = await _user(session, 100, "inviter")
    invited = await _user(session, 200, "newbie")

    assert await referral_service.attach(session, invited, inviter.telegram_id) is True
    # Bog'lash pulni BERMAYDI — mukofot obunadan keyin.
    assert Decimal(str(inviter.balance or 0)) == Decimal(0)

    result = await referral_service.reward(session, invited)

    assert result is not None
    rewarded, amount = result
    assert rewarded.id == inviter.id
    assert amount == Decimal(1000)
    assert Decimal(str(inviter.balance)) == Decimal(1000)

    transaction = (
        await session.execute(
            select(BalanceTransaction).where(BalanceTransaction.user_id == inviter.id)
        )
    ).scalar_one()
    assert transaction.kind == TransactionKind.REFERRAL
    assert Decimal(str(transaction.balance_after)) == Decimal(str(inviter.balance))


@pytest.mark.asyncio
async def test_reward_is_paid_only_once(session) -> None:
    """"Tekshirish" tugmasi bir necha marta bosilishi mumkin."""
    await _bonus(session, Decimal(1000))
    inviter = await _user(session, 101)
    invited = await _user(session, 201)
    await referral_service.attach(session, invited, inviter.telegram_id)

    assert await referral_service.reward(session, invited) is not None
    assert await referral_service.reward(session, invited) is None

    assert Decimal(str(inviter.balance)) == Decimal(1000)
    rows = (
        await session.execute(
            select(BalanceTransaction).where(BalanceTransaction.user_id == inviter.id)
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_cannot_invite_yourself(session) -> None:
    user = await _user(session, 102)

    assert await referral_service.attach(session, user, user.telegram_id) is False
    assert user.referred_by_id is None


@pytest.mark.asyncio
async def test_unknown_referrer_is_ignored(session) -> None:
    """Havoladagi id bilan hech kim topilmasa, bog'lanish yozilmaydi."""
    user = await _user(session, 103)

    assert await referral_service.attach(session, user, 999999) is False
    assert user.referred_by_id is None


@pytest.mark.asyncio
async def test_second_referrer_cannot_overwrite_the_first(session) -> None:
    first = await _user(session, 104)
    second = await _user(session, 105)
    invited = await _user(session, 204)

    assert await referral_service.attach(session, invited, first.telegram_id) is True
    assert await referral_service.attach(session, invited, second.telegram_id) is False
    assert invited.referred_by_id == first.id


@pytest.mark.asyncio
async def test_zero_bonus_stops_the_programme(session) -> None:
    """Admin summani 0 qilsa, hech kimga pul berilmaydi."""
    await _bonus(session, Decimal(0))
    inviter = await _user(session, 106)
    invited = await _user(session, 206)
    await referral_service.attach(session, invited, inviter.telegram_id)

    assert await referral_service.reward(session, invited) is None
    assert Decimal(str(inviter.balance or 0)) == Decimal(0)
    # Bayroq ham yoqilmaydi: summa qaytarilsa mukofot keyin berilishi mumkin.
    assert invited.referral_rewarded is False


@pytest.mark.asyncio
async def test_reward_without_referrer_does_nothing(session) -> None:
    await _bonus(session, Decimal(1000))
    user = await _user(session, 107)

    assert await referral_service.reward(session, user) is None


@pytest.mark.asyncio
async def test_count_invited(session) -> None:
    inviter = await _user(session, 108)
    for telegram_id in (301, 302, 303):
        invited = await _user(session, telegram_id)
        await referral_service.attach(session, invited, inviter.telegram_id)

    assert await referral_service.count_invited(session, inviter) == 3
