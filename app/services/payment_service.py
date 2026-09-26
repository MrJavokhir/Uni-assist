"""Balans va to'lov mantig'i.

Bu yerda balansga tegadigan HAMMA amal jamlangan. Sabab: qoldiq
(`users.balance`) va tarix (`balance_transactions`) doim bir-biriga mos
bo'lishi kerak. Ikkalasini alohida-alohida joylarda yangilasak, bir kun
kelib biri o'zgarib, ikkinchisi qolib ketadi va qaysi biri to'g'riligini
aniqlash imkonsiz bo'ladi.

Shuning uchun qoldiq HECH QAYERDA to'g'ridan-to'g'ri o'zgartirilmaydi —
faqat `_apply()` orqali, u esa har safar tranzaksiya yozuvini ham yaratadi.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AdmissionService,
    BalanceTransaction,
    BotAdmin,
    Payment,
    PaymentSettings,
    PaymentStatus,
    TransactionKind,
    User,
)

logger = logging.getLogger(__name__)


async def get_settings(session: AsyncSession) -> PaymentSettings:
    """Karta rekvizitlari. Yozuv migratsiyada yaratilgan (id=1).

    Baza qo'lda tozalangan bo'lsa ham bot yiqilmasligi kerak, shuning uchun
    yozuv topilmasa yangisi yaratiladi.
    """
    row = (await session.execute(select(PaymentSettings).limit(1))).scalar_one_or_none()
    if row is None:
        row = PaymentSettings(id=1)
        session.add(row)
        await session.flush()
    return row


async def active_admin_ids(session: AsyncSession) -> list[int]:
    stmt = select(BotAdmin.telegram_id).where(BotAdmin.is_active.is_(True))
    return list((await session.execute(stmt)).scalars().all())


async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    stmt = select(BotAdmin.id).where(
        BotAdmin.telegram_id == telegram_id, BotAdmin.is_active.is_(True)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _apply(
    session: AsyncSession,
    user: User,
    amount: Decimal,
    kind: TransactionKind,
    *,
    payment_id: int | None = None,
    service_id: int | None = None,
    note: str | None = None,
) -> BalanceTransaction:
    """Qoldiqni o'zgartiradi va o'zgarishni tarixga yozadi.

    `amount` ishorali: musbat — qo'shiladi, manfiy — yechiladi.
    Balansni o'zgartirishning boshqa yo'li yo'q.
    """
    current = Decimal(str(user.balance or 0))
    new_balance = current + amount
    user.balance = new_balance

    transaction = BalanceTransaction(
        user_id=user.id,
        amount=amount,
        balance_after=new_balance,
        kind=kind,
        payment_id=payment_id,
        service_id=service_id,
        note=note,
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def start_topup(session: AsyncSession, user: User, amount: Decimal) -> Payment:
    """Yangi to'ldirish urinishi — chek hali yuborilmagan."""
    settings_row = await get_settings(session)
    payment = Payment(
        user_id=user.id,
        amount=amount,
        currency=settings_row.currency,
        status=PaymentStatus.AWAITING_RECEIPT,
    )
    session.add(payment)
    await session.flush()
    return payment


async def latest_open_payment(session: AsyncSession, user: User) -> Payment | None:
    """Foydalanuvchining hali yopilmagan oxirgi to'lovi.

    Chek yuborilganda aynan shu yozuvga biriktiriladi — foydalanuvchi
    summani kiritgandan keyin boshqa yozuv yaratmaydi.
    """
    stmt = (
        select(Payment)
        .where(
            Payment.user_id == user.id,
            Payment.status.in_([PaymentStatus.AWAITING_RECEIPT, PaymentStatus.SUBMITTED]),
        )
        .order_by(Payment.id.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def attach_receipt(
    session: AsyncSession, payment: Payment, file_id: str, kind: str
) -> Payment:
    payment.receipt_file_id = file_id
    payment.receipt_kind = kind
    payment.status = PaymentStatus.SUBMITTED
    await session.flush()
    return payment


async def approve_payment(
    session: AsyncSession, payment: Payment, admin_telegram_id: int
) -> Decimal:
    """To'lovni tasdiqlaydi va balansni to'ldiradi.

    Takroriy /approve xavfsiz: allaqachon tasdiqlangan to'lov ikkinchi
    marta balansga qo'shilmaydi.
    """
    if payment.status == PaymentStatus.APPROVED:
        logger.info("To'lov #%s allaqachon tasdiqlangan, qayta qo'shilmadi", payment.id)
        return Decimal(str(payment.user.balance or 0))

    payment.status = PaymentStatus.APPROVED
    payment.reviewed_by = admin_telegram_id
    transaction = await _apply(
        session,
        payment.user,
        Decimal(str(payment.amount)),
        TransactionKind.TOPUP,
        payment_id=payment.id,
        note="Balans to'ldirildi",
    )
    return Decimal(str(transaction.balance_after))


async def reject_payment(
    session: AsyncSession, payment: Payment, admin_telegram_id: int, note: str | None = None
) -> None:
    payment.status = PaymentStatus.REJECTED
    payment.reviewed_by = admin_telegram_id
    if note:
        payment.admin_note = note
    await session.flush()


class InsufficientBalance(Exception):
    """Xizmat narxi qoldiqdan katta."""

    def __init__(self, needed: Decimal, available: Decimal) -> None:
        self.needed = needed
        self.available = available
        super().__init__(f"Balans yetmaydi: kerak {needed}, bor {available}")


async def charge_service(
    session: AsyncSession, user: User, service: AdmissionService
) -> Decimal:
    """Xizmat narxini balansdan yechadi.

    Narxi ko'rsatilmagan xizmat (`price_amount is None`) pulsiz o'tadi —
    u "narx kelishiladi" degani, summani bu yerda taxmin qilib bo'lmaydi.
    """
    if service.price_amount is None:
        return Decimal(str(user.balance or 0))

    price = Decimal(str(service.price_amount))
    available = Decimal(str(user.balance or 0))
    if price > available:
        raise InsufficientBalance(price, available)

    transaction = await _apply(
        session,
        user,
        -price,
        TransactionKind.SERVICE,
        service_id=service.id,
        note=service.title_uz,
    )
    return Decimal(str(transaction.balance_after))
