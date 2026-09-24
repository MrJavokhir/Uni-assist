import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, VerificationMixin, str_enum
from app.db.models.program import DeadlineType, deadline_type_enum

if TYPE_CHECKING:
    from app.db.models.country import Country
    from app.db.models.program import Program

program_scholarship = Table(
    "program_scholarship",
    Base.metadata,
    Column("program_id", ForeignKey("programs.id", ondelete="CASCADE"), primary_key=True),
    Column("scholarship_id", ForeignKey("scholarships.id", ondelete="CASCADE"), primary_key=True),
)

# Davlat stipendiyalari (DAAD, Chevening, Erasmus Mundus va h.k.) aniq bitta
# dasturga emas, butun davlatga tegishli bo'ladi. Many-to-many tanlandi, chunki
# Erasmus Mundus kabi grantlar bir nechta davlatni qamrab oladi — nullable FK
# buni ifodalay olmasdi.
scholarship_country = Table(
    "scholarship_country",
    Base.metadata,
    Column("scholarship_id", ForeignKey("scholarships.id", ondelete="CASCADE"), primary_key=True),
    Column("country_id", ForeignKey("countries.id", ondelete="CASCADE"), primary_key=True),
)


class CoverageType(str, enum.Enum):
    FULL = "full"
    PARTIAL = "partial"
    CONTRACT_ONLY = "contract_only"


class UniversityChoiceType(str, enum.Enum):
    ASSIGNED_BY_SCHOLARSHIP = "assigned_by_scholarship"
    USER_CHOOSES = "user_chooses"


class Scholarship(TimestampMixin, VerificationMixin, Base):
    __tablename__ = "scholarships"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tavsif uch tilda — `description` o'zbekcha (asosiy), qolganlari bo'sh
    # bo'lsa Mini App o'zbekchasiga qaytadi.
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Logotip. Bo'sh bo'lsa `source_url` domenidan avtomatik olinadi.
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    coverage_type: Mapped[CoverageType] = mapped_column(
        str_enum(CoverageType, "coverage_type"), nullable=False
    )
    coverage_percent: Mapped[int | None] = mapped_column(nullable=True)
    stipend_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Stipendiya daraja bo'yicha farq qiladi (masalan DAAD magistr/PhD uchun
    # har xil) — shuning uchun oraliq saqlanadi.
    stipend_max: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    stipend_period: Mapped[str | None] = mapped_column(String(10), nullable=True)  # month|year
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # --- Talablar (raqam/kalit sifatida: interfeys ularni o'z tilida yozadi) ---
    ielts_min: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    toefl_min: Mapped[int | None] = mapped_column(nullable=True)
    # 0 = talab qilinmaydi, None = ko'rsatilmagan
    work_experience_years: Mapped[int | None] = mapped_column(nullable=True)
    # Qaysi darajalarga beriladi: ["bachelor", "master", "phd"]
    degree_levels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # O'qish tili — kanonik inglizcha nom ("English"), Mini App o'giradi
    study_language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_min_years: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    duration_max_years: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    # Tanlov necha bosqichdan iborat (hujjat -> test -> suhbat ...)
    selection_stages: Mapped[int | None] = mapped_column(nullable=True)

    extras_flight: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extras_insurance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extras_dormitory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extras_language_course: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Qaysi universitet(lar)da o'qiladi: konsorsium a'zolari yoki tanlov qoidasi
    # ("Germaniyadagi istalgan davlat tan olgan universitet").
    # Asosiy ustun o'zbekcha; `_ru`/`_en` bo'sh bo'lsa Mini App o'zbekchasiga
    # qaytadi — `description` bilan bir xil qoida.
    universities_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    universities_text_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    universities_text_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Kim tanlaydi: komissiya, elchixona, vazirlik.
    selected_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_by_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_by_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Erkin matnli talablar — har bir qator alohida ko'rsatiladi.
    requirements_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements_text_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements_text_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    age_limit: Mapped[int | None] = mapped_column(nullable=True)
    citizenship_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    university_choice: Mapped[UniversityChoiceType] = mapped_column(
        str_enum(UniversityChoiceType, "university_choice_type"), nullable=False
    )
    application_linked_to_program: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    programs: Mapped[list["Program"]] = relationship(
        secondary=program_scholarship, back_populates="scholarships"
    )
    countries: Mapped[list["Country"]] = relationship(
        secondary=scholarship_country, back_populates="scholarships"
    )
    deadlines: Mapped[list["ScholarshipDeadline"]] = relationship(
        back_populates="scholarship", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.name


class ScholarshipDeadline(Base):
    __tablename__ = "scholarship_deadlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    scholarship_id: Mapped[int] = mapped_column(ForeignKey("scholarships.id", ondelete="CASCADE"))
    type: Mapped[DeadlineType] = mapped_column(deadline_type_enum, nullable=False)
    date_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    intake_term: Mapped[str] = mapped_column(String(50), nullable=False)

    scholarship: Mapped["Scholarship"] = relationship(back_populates="deadlines")

    def __str__(self) -> str:
        return f"{self.type.value} — {self.date_utc:%Y-%m-%d}"
