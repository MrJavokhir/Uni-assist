from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.country import Country
    from app.db.models.program import Program


class University(TimestampMixin, Base):
    __tablename__ = "universities"

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    website: Mapped[str] = mapped_column(String(500), nullable=True)
    # Logotip havolasi. Bo'sh bo'lsa Mini App uni `website` domenidan
    # avtomatik oladi (Google favicon xizmati), u ham bo'lmasa universitet
    # nomining bosh harflarini chizadi.
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Universitet joylashgan hudud vaqt zonasi (masalan "Europe/Berlin") —
    # deadline'larni foydalanuvchiga Toshkent vaqtida ko'rsatish uchun kerak.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    country: Mapped["Country"] = relationship(back_populates="universities")
    programs: Mapped[list["Program"]] = relationship(
        back_populates="university", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.name
