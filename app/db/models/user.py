import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, str_enum
from app.db.models.program import DegreeLevel, GpaScale, degree_level_enum, gpa_scale_enum

if TYPE_CHECKING:
    from app.db.models.country import Country
    from app.db.models.field import Field
    from app.db.models.program import Program

user_target_country = Table(
    "user_target_country",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("country_id", ForeignKey("countries.id", ondelete="CASCADE"), primary_key=True),
)


class UiLanguage(str, enum.Enum):
    UZ = "uz"
    RU = "ru"
    EN = "en"


class LanguageCertType(str, enum.Enum):
    IELTS = "IELTS"
    TOEFL = "TOEFL"
    DELE = "DELE"
    TESTDAF = "TestDAF"
    OTHER = "other"


class UniversityRankRange(str, enum.Enum):
    """Foydalanuvchi mo'ljallagan universitet reytingi (jahon reytingidagi o'rin).

    Tanlanmagan bo'lsa (None) — reyting muhim emas.
    """

    TOP_100 = "1-100"
    TOP_300 = "101-300"
    TOP_500 = "301-500"
    BELOW_500 = "500+"


university_rank_range_enum = str_enum(UniversityRankRange, "university_rank_range")


class OtherTestType(str, enum.Enum):
    GRE = "GRE"
    GMAT = "GMAT"


class SavedProgramStatus(str, enum.Enum):
    PLANNING = "planning"
    APPLIED = "applied"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ui_language: Mapped[UiLanguage] = mapped_column(
        str_enum(UiLanguage, "ui_language"), nullable=False, default=UiLanguage.UZ
    )

    # Profil to'liqsiz ham saqlanadi — barcha quyidagi maydonlar ixtiyoriy (nullable).
    gpa_raw: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    gpa_scale: Mapped[GpaScale | None] = mapped_column(gpa_scale_enum, nullable=True)
    degree_level: Mapped[DegreeLevel | None] = mapped_column(degree_level_enum, nullable=True)
    # Tanlangan yo'nalish (`fields` ma'lumotnomasidan). Moslik qidiruvi
    # dasturlarni shu bo'yicha chegaralaydi.
    field_id: Mapped[int | None] = mapped_column(
        ForeignKey("fields.id", ondelete="SET NULL"), nullable=True
    )
    # Eski erkin matnli yo'nalish — faqat o'qish uchun, keyinroq o'chiriladi.
    major_legacy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    budget_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    # Mo'ljaldagi universitet reytingi (jahon reytingidagi o'rin oralig'i).
    university_rank_range: Mapped[UniversityRankRange | None] = mapped_column(
        university_rank_range_enum, nullable=True
    )
    # Ariza to'lovi (application fee) bor dasturlar ham mos keladimi.
    # True = to'lovga rozi, False = faqat bepul ariza, None = tanlanmagan.
    application_fee_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Balans: faqat tasdiqlangan to'lov orqali oshadi va Admission Kit
    # xizmatlariga sarflanadi. Har bir o'zgarish `balance_transactions` da
    # yoziladi, shuning uchun qoldiqni tarix bilan solishtirib tekshirish
    # mumkin (app/db/models/payment.py).
    balance: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, server_default="0"
    )
    # Botdagi `/blockuser` buyrug'i qo'yadi: bloklangan odamdan to'lov
    # qabul qilinmaydi.
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    field: Mapped["Field | None"] = relationship()
    target_countries: Mapped[list["Country"]] = relationship(secondary=user_target_country)
    language_certificates: Mapped[list["UserLanguageCertificate"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    other_tests: Mapped[list["UserOtherTest"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    saved_programs: Mapped[list["SavedProgram"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.username or str(self.telegram_id)


class UserLanguageCertificate(Base):
    __tablename__ = "user_language_certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[LanguageCertType] = mapped_column(
        str_enum(LanguageCertType, "language_cert_type"), nullable=False
    )
    score: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)

    user: Mapped["User"] = relationship(back_populates="language_certificates")

    def __str__(self) -> str:
        return f"{self.type.value}: {self.score}"


class UserOtherTest(Base):
    __tablename__ = "user_other_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[OtherTestType] = mapped_column(
        str_enum(OtherTestType, "other_test_type"), nullable=False
    )
    score: Mapped[int] = mapped_column(nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)

    user: Mapped["User"] = relationship(back_populates="other_tests")

    def __str__(self) -> str:
        return f"{self.type.value}: {self.score}"


class SavedProgram(TimestampMixin, Base):
    __tablename__ = "saved_programs"
    __table_args__ = (UniqueConstraint("user_id", "program_id", name="uq_saved_program"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"))
    status: Mapped[SavedProgramStatus] = mapped_column(
        str_enum(SavedProgramStatus, "saved_program_status"),
        nullable=False,
        default=SavedProgramStatus.PLANNING,
    )
    # Foydalanuvchi "Ariza berdim" bosganda shu dastur bo'yicha eslatmalar to'xtaydi.
    reminders_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="saved_programs")
    program: Mapped["Program"] = relationship(back_populates="saved_by_users")

    def __str__(self) -> str:
        return f"user={self.user_id} program={self.program_id}"
