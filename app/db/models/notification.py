"""Deadline eslatmalari: yuborilgan xabarlar jurnali va foydalanuvchi takliflari."""

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, str_enum

if TYPE_CHECKING:
    from app.db.models.program import Program
    from app.db.models.user import User


class NotificationType(str, enum.Enum):
    """Bitta saqlangan dastur uchun yuborilishi mumkin bo'lgan xabar turlari.

    Rejalashtirilganlari ko'pi bilan IKKITA: `exact` dastur uchun 14 va 3
    kunlik, `month` uchun oldingi oy va shu oy boshi, `unknown` uchun bitta
    tekshiruv eslatmasi. `exact_immediate` — istisno: dastur deadline'ga yaqin
    qolganda saqlansa, o'sha zahoti yuboriladi.
    """

    EXACT_14D = "exact_14d"
    EXACT_3D = "exact_3d"
    EXACT_IMMEDIATE = "exact_immediate"
    MONTH_BEFORE = "month_before"
    MONTH_START = "month_start"
    UNKNOWN_CHECK = "unknown_check"


class SuggestionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class NotificationLog(Base):
    """Yuborilgan har bir xabar. Dublikat nazorati SHU jadval orqali.

    Ilgari bu Redis kalitlari bilan qilinardi. Jadval uch sababdan afzal:
    Redis tozalansa eslatmalar qaytadan ketmaydi; "bosildi" ko'rsatkichini
    yozib borish mumkin; adminkadagi statistika shundan o'qiladi.
    """

    __tablename__ = "notification_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", "notif_type", name="uq_notification_once"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True
    )
    notif_type: Mapped[NotificationType] = mapped_column(
        str_enum(NotificationType, "notification_type"), nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    clicked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped["User"] = relationship()
    program: Mapped["Program"] = relationship()

    def __str__(self) -> str:
        return f"{self.notif_type.value} -> user={self.user_id} program={self.program_id}"


class DeadlineSuggestion(TimestampMixin, Base):
    """Foydalanuvchi taklif qilgan deadline sanasi.

    Deadline'i noma'lum dasturlarda Mini App "Sanani bilaman" formasini
    ko'rsatadi. Taklif to'g'ridan-to'g'ri katalogga yozilmaydi — admin uni
    tasdiqlagandan keyingina `deadlines` jadvaliga tushadi, chunki katalogdagi
    har bir sana rasmiy manbaga asoslanishi kerak.
    """

    __tablename__ = "deadline_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True
    )
    suggested_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[SuggestionStatus] = mapped_column(
        str_enum(SuggestionStatus, "suggestion_status"),
        nullable=False,
        default=SuggestionStatus.PENDING,
        server_default=SuggestionStatus.PENDING.value,
        index=True,
    )

    user: Mapped["User"] = relationship()
    program: Mapped["Program"] = relationship()

    def __str__(self) -> str:
        return f"program={self.program_id} -> {self.suggested_date}"
