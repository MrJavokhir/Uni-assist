"""Mentordan so'rash — savollar, yozishma, shikoyatlar va davlat topic'lari.

Foydalanuvchi Mini App'dan savol beradi, savol mentorlar forum-guruhidagi
o'sha davlat topic'iga tushadi, mentor guruhda javob yozadi, bot esa
javobni foydalanuvchiga ANONIM yetkazadi.

MENTORLAR JADVALI YO'Q — ataylab. Mentorni guruhga admin qo'lda qo'shadi va
chiqaradi; guruh a'zoligining o'zi mentorlik huquqi. Shuning uchun bu
yerda mentor faqat Telegram ID va ism sifatida, savol/xabar yonida
saqlanadi (adminka uchun) — alohida ro'yxat sifatida emas.

Maxfiylik qoidasi ikki tomonlama:
  * guruhda foydalanuvchining ismi, username'i va ID'si ko'rinmaydi;
  * foydalanuvchiga mentorning ismi hech qayerda ko'rsatilmaydi
    (`claimed_by_name`, `mentor_name` — faqat adminka uchun).
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Sequence,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, str_enum

if TYPE_CHECKING:
    from app.db.models.user import User


class MentorLevel(str, enum.Enum):
    BACHELOR = "bachelor"
    MASTER = "master"


class MentorTopic(str, enum.Enum):
    ADMISSION = "admission"
    DOCUMENTS = "documents"
    VISA = "visa"
    LIVING = "living"
    WORK = "work"
    STUDIES = "studies"
    OTHER = "other"


class MentorQuestionStatus(str, enum.Enum):
    """Savol holati.

    OPEN     — mentor kutilyapti, guruhda "Javob berish" tugmasi bor;
    CLAIMED  — mentor oldi, javobi kutilyapti (qo'shimcha savolda ham);
    ANSWERED — javob berildi, foydalanuvchi qo'shimcha savol yozishi mumkin;
    CLOSED   — yopildi (foydalanuvchi, admin yoki 72 soatdan keyin avtomatik).
    """

    OPEN = "open"
    CLAIMED = "claimed"
    ANSWERED = "answered"
    CLOSED = "closed"


class MentorSender(str, enum.Enum):
    USER = "user"
    MENTOR = "mentor"


class ComplaintStatus(str, enum.Enum):
    NEW = "new"
    REVIEWED = "reviewed"


class ComplaintReason(str, enum.Enum):
    WRONG_INFO = "wrong_info"
    DISRESPECT = "disrespect"
    PAID_OR_AD = "paid_or_ad"
    OTHER = "other"


# Foydalanuvchiga ko'rinadigan raqam (#148). `id` dan alohida: ketma-ket
# id savollar sonini oshkor qilardi va bo'sh boshlanardi (#1, #2...).
PUBLIC_NUMBER_SEQ = Sequence("mentor_question_number_seq", start=100)


class CountryTopic(Base):
    """Davlat -> guruhdagi topic. Topic birinchi savol kelganda yaratiladi."""

    __tablename__ = "country_topics"

    country_code: Mapped[str] = mapped_column(String(2), primary_key=True)
    message_thread_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MentorQuestion(Base):
    __tablename__ = "mentor_questions"
    __table_args__ = (
        CheckConstraint("rating is null or rating between 1 and 5", name="ck_mentor_rating"),
        Index("ix_mentor_questions_user_created", "user_id", "created_at"),
        Index("ix_mentor_questions_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_number: Mapped[int] = mapped_column(
        Integer,
        PUBLIC_NUMBER_SEQ,
        server_default=PUBLIC_NUMBER_SEQ.next_value(),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    level: Mapped[MentorLevel] = mapped_column(
        str_enum(MentorLevel, "mentor_level"), nullable=False
    )
    topic: Mapped[MentorTopic] = mapped_column(
        str_enum(MentorTopic, "mentor_topic"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MentorQuestionStatus] = mapped_column(
        str_enum(MentorQuestionStatus, "mentor_question_status"),
        nullable=False,
        default=MentorQuestionStatus.OPEN,
        server_default=MentorQuestionStatus.OPEN.value,
    )

    claimed_by_tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    claimed_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Guruhdagi savol xabari ("Javob berish" tugmasi shunda turadi).
    group_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Mentor javobini aynan shu xabarga reply qilib yozadi. Javob qabul
    # qilingach tozalanadi — eski ForceReply'ga yozilgan xabar e'tiborsiz.
    force_reply_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # BIRINCHI javob vaqti — adminkadagi "javob vaqti" shundan hisoblanadi.
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reminder_24h_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Yoqilgan bo'lsa savol OYLIK LIMITGA SANALMAYDI: foydalanuvchi
    # mentorlar bandligi uchun jazolanmasligi kerak.
    user_notified_48h: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    admin_notified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped["User"] = relationship()
    messages: Mapped[list["MentorMessage"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="MentorMessage.id",
    )
    complaints: Mapped[list["MentorComplaint"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="MentorComplaint.id",
    )


class MentorMessage(Base):
    """Yozishma tarixi. Asl savol ham birinchi xabar sifatida yoziladi —
    chat ekrani va adminka tarixni bitta joydan o'qiydi."""

    __tablename__ = "mentor_messages"
    __table_args__ = (Index("ix_mentor_messages_question", "question_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("mentor_questions.id", ondelete="CASCADE"), nullable=False
    )
    sender: Mapped[MentorSender] = mapped_column(
        str_enum(MentorSender, "mentor_sender"), nullable=False
    )
    # Faqat mentor xabarlarida. Foydalanuvchiga HECH QACHON berilmaydi.
    mentor_tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mentor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    question: Mapped[MentorQuestion] = relationship(back_populates="messages")


class MentorComplaint(Base):
    __tablename__ = "mentor_complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("mentor_questions.id", ondelete="CASCADE"), nullable=False
    )
    # Shikoyat aniq bir mentor xabariga bo'lsa. Savolning o'ziga ham bo'lishi mumkin.
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("mentor_messages.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[ComplaintReason] = mapped_column(
        str_enum(ComplaintReason, "mentor_complaint_reason"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ComplaintStatus] = mapped_column(
        str_enum(ComplaintStatus, "mentor_complaint_status"),
        nullable=False,
        default=ComplaintStatus.NEW,
        server_default=ComplaintStatus.NEW.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    question: Mapped[MentorQuestion] = relationship(back_populates="complaints")
    message: Mapped[MentorMessage | None] = relationship()
