import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, VerificationMixin, str_enum

if TYPE_CHECKING:
    from app.db.models.scholarship import Scholarship
    from app.db.models.university import University
    from app.db.models.user import SavedProgram


class DegreeLevel(str, enum.Enum):
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"


class GpaScale(str, enum.Enum):
    SCALE_4 = "4"
    SCALE_5 = "5"
    SCALE_100 = "100"


class DeadlineType(str, enum.Enum):
    APPLICATION_OPEN = "application_open"
    APPLICATION_CLOSE = "application_close"
    DOCUMENT = "document"
    VISA = "visa"


# Shared Enum instance'lar — bir nechta jadvalda bir xil Postgres enum turidan
# foydalanish uchun (masalan Program va Scholarship deadline'lari, yoki
# User va Program'dagi degree_level/gpa_scale) — DDL ikki marta yaratilmasin uchun bitta joyda e'lon qilinadi.
deadline_type_enum = str_enum(DeadlineType, "deadline_type")
degree_level_enum = str_enum(DegreeLevel, "degree_level")
gpa_scale_enum = str_enum(GpaScale, "gpa_scale")


class Program(TimestampMixin, VerificationMixin, Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    university_id: Mapped[int] = mapped_column(ForeignKey("universities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Diplomaning qisqartmasi — LLM, MBA, B.Sc., M.Eng. va h.k. Talabalar
    # dasturlarni ko'pincha aynan shu qisqartma bo'yicha izlaydi.
    abbreviation: Mapped[str | None] = mapped_column(String(30), nullable=True)
    degree_level: Mapped[DegreeLevel] = mapped_column(degree_level_enum, nullable=False)
    field_of_study: Mapped[str] = mapped_column(String(255), nullable=False)
    language_of_instruction: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_years: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    intake_term: Mapped[str] = mapped_column(String(50), nullable=False)
    # Erkin izoh uch tilda. `notes` — o'zbekcha (asosiy); qolganlari bo'sh
    # bo'lsa Mini App o'zbekchasiga qaytadi.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Rasmiy sahifada ko'rsatilmagan maydonlar KALITLARI ("tuition", "ielts"...).
    # Ilgari bu ma'lumot izoh matniga o'zbekcha yozib qo'yilardi va ruscha/
    # inglizcha interfeysda ham o'zbekcha chiqib qolardi. Endi kalit saqlanadi,
    # jumlani esa Mini App foydalanuvchi tilida o'zi yasaydi.
    missing_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Ariza uchun kerakli hujjatlar — KALITLAR ro'yxati ("transcript", "cv"...).
    # Matn emas, kalit saqlanadi: Mini App ularni foydalanuvchi tilida yozadi.
    required_documents: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Shu dasturning O'ZIGA tegishli stipendiya bormi (universitet/fakultet
    # stipendiyasi). None = tekshirilmagan.
    has_scholarship: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    scholarship_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    university: Mapped["University"] = relationship(back_populates="programs")
    requirement: Mapped["ProgramRequirement"] = relationship(
        back_populates="program", cascade="all, delete-orphan", uselist=False
    )
    cost: Mapped["ProgramCost"] = relationship(
        back_populates="program", cascade="all, delete-orphan", uselist=False
    )
    deadlines: Mapped[list["Deadline"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )
    scholarships: Mapped[list["Scholarship"]] = relationship(
        secondary="program_scholarship", back_populates="programs"
    )
    saved_by_users: Mapped[list["SavedProgram"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.name


class ProgramRequirement(Base):
    __tablename__ = "program_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), unique=True
    )

    gpa_min: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    gpa_scale: Mapped[GpaScale | None] = mapped_column(gpa_scale_enum, nullable=True)
    ielts_min: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    toefl_min: Mapped[int | None] = mapped_column(nullable=True)
    gre_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gre_min: Mapped[int | None] = mapped_column(nullable=True)
    prereq_major: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_limit: Mapped[int | None] = mapped_column(nullable=True)

    program: Mapped["Program"] = relationship(back_populates="requirement")

    def __str__(self) -> str:
        return f"Talablar #{self.program_id}"


class ProgramCost(Base):
    __tablename__ = "program_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), unique=True
    )

    tuition_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # Vizaga isbotlanishi kerak bo'lgan summa (kontraktdan alohida — Sperrkonto, GIC va h.k.)
    visa_proof_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    living_cost_monthly: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Bu raqamlar yiliga o'zgaradi — hardcode qilinmaydi, oxirgi tekshiruv sanasi saqlanadi
    last_checked: Mapped[date] = mapped_column(Date, nullable=False)

    program: Mapped["Program"] = relationship(back_populates="cost")

    def __str__(self) -> str:
        return f"Xarajat #{self.program_id}"


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"))
    type: Mapped[DeadlineType] = mapped_column(deadline_type_enum, nullable=False)
    # UTC'da saqlanadi; foydalanuvchiga ko'rsatishda Toshkent vaqtiga o'giriladi.
    date_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    intake_term: Mapped[str] = mapped_column(String(50), nullable=False)

    program: Mapped["Program"] = relationship(back_populates="deadlines")

    def __str__(self) -> str:
        return f"{self.type.value} — {self.date_utc:%Y-%m-%d}"
