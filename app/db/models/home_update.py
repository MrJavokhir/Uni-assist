import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, str_enum

if TYPE_CHECKING:
    from app.db.models.scholarship import Scholarship


class UpdateKind(str, enum.Enum):
    """Yangilik turi — Mini App'da rangli nuqta va yorliq shundan."""

    NEW = "new"  # yangi grant/katalog qo'shildi
    OPEN = "open"  # ariza qabuli ochildi
    DEADLINE = "deadline"  # muddat o'zgardi
    INFO = "info"  # boshqa yangilik


class HomeUpdate(TimestampMixin, Base):
    """Mini App bosh sahifasi pastidagi "Yangiliklar" ro'yxati.

    Admin panelda qo'lda yoziladi. Grant tanlansa, yangilik bosilganda
    o'sha grant sahifasi ochiladi.
    """

    __tablename__ = "home_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sarlavha uch tilda — `title` o'zbekcha (asosiy), qolganlari bo'sh
    # bo'lsa Mini App o'zbekchasini ko'rsatadi.
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    title_ru: Mapped[str | None] = mapped_column(String(200), nullable=True)
    title_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    kind: Mapped[UpdateKind] = mapped_column(
        str_enum(UpdateKind, "update_kind"), nullable=False, default=UpdateKind.NEW
    )
    published_on: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today, server_default=func.current_date()
    )
    scholarship_id: Mapped[int | None] = mapped_column(
        ForeignKey("scholarships.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    scholarship: Mapped["Scholarship | None"] = relationship()

    def __str__(self) -> str:
        return self.title
