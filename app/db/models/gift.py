"""Bosh sahifadagi sovg'a qutisi.

Admin Admission Kit bo'limida sovg'alar ro'yxatini tuzadi: har biri — Kit
xizmatiga chegirma (100% = bepul) va tushish ehtimoli foizda (`weight`). User qutini
bir marta ochadi va faol sovg'alardan biri tasodifan tushadi (`UserGift`).
Sovg'a o'sha xizmatni olganda (yoki so'rov yuborganda) ishlatiladi.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.service import AdmissionService
    from app.db.models.user import User


class Gift(TimestampMixin, Base):
    __tablename__ = "gifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("admission_services.id", ondelete="CASCADE"), index=True
    )
    # Chegirma foizi: 1–100. 100 — xizmat bepul.
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    # Tushish ehtimoli foizda (1–100). Faol sovg'alar yig'indisi 100 bo'lmasa,
    # foizlar mutanosib hisoblanadi.
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    service: Mapped["AdmissionService"] = relationship()

    def __str__(self) -> str:
        title = self.service.title_uz if self.service else f"#{self.service_id}"
        return f"{title} — {self.discount_percent}%"


class UserGift(Base):
    """Userga tushgan sovg'a. Har bir userda ko'pi bilan bitta (quti bir marta ochiladi)."""

    __tablename__ = "user_gifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    gift_id: Mapped[int | None] = mapped_column(
        ForeignKey("gifts.id", ondelete="SET NULL"), nullable=True
    )
    # Ochilgan paytdagi qiymatlar: admin sovg'ani keyin o'zgartirsa ham,
    # userga va'da qilingani o'zgarmaydi.
    service_id: Mapped[int] = mapped_column(
        ForeignKey("admission_services.id", ondelete="CASCADE"), nullable=False
    )
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Xizmat olinganda (yoki so'rov yuborilganda) — sovg'a ishlatildi.
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    service: Mapped["AdmissionService"] = relationship()
    user: Mapped["User"] = relationship()
