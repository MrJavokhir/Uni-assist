from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def str_enum(enum_cls: type[PyEnum], name: str, **kwargs) -> SAEnum:
    """Postgres native enum ustunini yaratadi va Python Enum'ning `.value`sini
    (nomini emas) DB qatoriga saqlaydi — masalan GpaScale.SCALE_4 -> '4'."""
    return SAEnum(enum_cls, name=name, values_callable=lambda x: [e.value for e in x], **kwargs)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """created_at / updated_at — har bir jadvalda audit uchun."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VerificationMixin:
    """source_url / verified_at / verified_by — ma'lumot sifatini kafolatlash uchun majburiy maydonlar."""

    source_url: Mapped[str] = mapped_column(nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_by: Mapped[str] = mapped_column(nullable=False)
