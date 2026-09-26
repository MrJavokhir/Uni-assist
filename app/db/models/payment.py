"""Balans, to'lovlar va ular bilan bog'liq sozlamalar.

To'lov QO'LDA tasdiqlanadi: foydalanuvchi kartaga pul o'tkazadi, chek
rasmini botga yuboradi, admin botda `/approve` yozadi va balans shundan
keyin to'ldiriladi. Avtomatik to'lov tizimi (Payme/Click) ulanmagan.

Pul miqdorlari `Numeric` da saqlanadi — `float` da 10 000.10 kabi summalar
yig'ilganda xato to'planadi.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, str_enum

if TYPE_CHECKING:
    from app.db.models.user import User


class PaymentStatus(str, enum.Enum):
    # Summa kiritilgan, chek hali yuborilmagan.
    AWAITING_RECEIPT = "awaiting_receipt"
    # Chek yuborilgan, admin ko'rib chiqishi kutilmoqda.
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class TransactionKind(str, enum.Enum):
    # Balans to'ldirildi (tasdiqlangan to'lov).
    TOPUP = "topup"
    # Admission Kit xizmati uchun yechildi.
    SERVICE = "service"
    # Admin qo'lda to'g'irlagan.
    ADJUSTMENT = "adjustment"


class PaymentSettings(TimestampMixin, Base):
    """Karta rekvizitlari va eng kam summa — adminkadan boshqariladi.

    Jadval ATAYLAB bitta qatorli: `id == 1` yozuvi o'qiladi. Bir nechta
    qator bo'lsa, qaysi biri amal qilishini aniqlash chalkash bo'lardi.
    """

    __tablename__ = "payment_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_number: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    card_holder: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    min_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=10000)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="UZS")

    def __str__(self) -> str:
        return f"Karta {self.card_number}" if self.card_number else "To'lov sozlamalari"


class BotAdmin(TimestampMixin, Base):
    """Botda `/approve`, `/reject`, `/blockuser` yoza oladigan odamlar.

    Adminka paroli bilan bog'liq emas: bu Telegram tomonidagi ruxsat.
    Chek kelganda xabar aynan shu ro'yxatdagilarga yuboriladi.
    """

    __tablename__ = "bot_admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __str__(self) -> str:
        return self.title or str(self.telegram_id)


class Payment(TimestampMixin, Base):
    """Bitta balans to'ldirish urinishi."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="UZS")
    status: Mapped[PaymentStatus] = mapped_column(
        str_enum(PaymentStatus, "payment_status"),
        nullable=False,
        default=PaymentStatus.AWAITING_RECEIPT,
    )
    # Telegram'dagi chek fayli. Rasmni o'zimizda saqlamaymiz — `file_id`
    # bo'yicha istalgan vaqt qayta yuborish mumkin.
    receipt_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)

    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship()

    def __str__(self) -> str:
        return f"To'lov #{self.id}"


class BalanceTransaction(TimestampMixin, Base):
    """Balansdagi har bir o'zgarish.

    `amount` ISHORALI: to'ldirish musbat, xizmat uchun yechish manfiy.
    `balance_after` ataylab saqlanadi — keyinchalik hisobni qayta yig'ib
    chiqmasdan, o'sha paytdagi qoldiqni ko'rish mumkin bo'lsin.
    """

    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    kind: Mapped[TransactionKind] = mapped_column(
        str_enum(TransactionKind, "transaction_kind"), nullable=False
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )
    service_id: Mapped[int | None] = mapped_column(
        ForeignKey("admission_services.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship()

    def __str__(self) -> str:
        return f"Tranzaksiya #{self.id}"
