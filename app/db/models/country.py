from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.scholarship import Scholarship
    from app.db.models.university import University


class Country(TimestampMixin, Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_uz: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    iso_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)

    universities: Mapped[list["University"]] = relationship(
        back_populates="country", cascade="all, delete-orphan"
    )
    # Davlat stipendiyalari (DAAD, Chevening...) — secondary satr ko'rinishida,
    # aylanma importni oldini olish uchun (Program.scholarships bilan bir uslubda).
    scholarships: Mapped[list["Scholarship"]] = relationship(
        secondary="scholarship_country", back_populates="countries"
    )

    def __str__(self) -> str:
        return self.name_uz
