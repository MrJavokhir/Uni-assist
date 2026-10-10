"""Mentordan so'rash — bazadagi mantiq (Telegram'siz).

Telegram bilan ishlash `mentor_group.py` da. Bu yerda faqat qaror va
holat: limitlar, atomik biriktirish, javobni tekshirish, yopish, baho.
Shu ajratish tufayli eng muhim qoidalarni soxta bot'siz test qilish
mumkin.

Holat o'zgarishlari SHARTLI UPDATE bilan qilinadi (`WHERE status = ...`):
ikki mentor bir vaqtda "Javob berish" bosganda yoki foydalanuvchi tugmani
ikki marta bosganda faqat bittasi o'tadi — baza buni kafolatlaydi.
"""

import enum
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import (
    ComplaintReason,
    Country,
    MentorComplaint,
    MentorLevel,
    MentorMessage,
    MentorQuestion,
    MentorQuestionStatus,
    MentorSender,
    MentorTopic,
    User,
)
from app.services.mentor_filter import find_violation
from app.services.timezone_utils import TASHKENT_TZ

QUESTION_MIN_CHARS = 30
QUESTION_MAX_CHARS = 1000
FOLLOWUP_MIN_CHARS = 2
ANSWER_MIN_CHARS = 50
COMMENT_MAX_CHARS = 1000

CLAIM_TIMEOUT = timedelta(hours=12)
REMIND_AFTER = timedelta(hours=24)
USER_NOTICE_AFTER = timedelta(hours=48)
AUTO_CLOSE_AFTER = timedelta(hours=72)

MEMBER_STATUSES = frozenset({"member", "administrator", "creator"})


class MentorError(Exception):
    """Foydalanuvchiga tushuntiriladigan rad etish. `code` — Mini App
    shu kod bo'yicha o'z tilida xabar ko'rsatadi."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AnswerVerdict(str, enum.Enum):
    IGNORE = "ignore"  # javob emas — mentorlar o'zaro gaplashyapti
    NOT_TEXT = "not_text"
    TOO_SHORT = "too_short"
    CONTACT = "contact"
    OK = "ok"


def now_utc() -> datetime:
    return datetime.now(UTC)


def is_enabled() -> bool:
    return bool(settings.bot_token and settings.mentor_group_id and settings.active_country_codes)


async def active_countries(session: AsyncSession) -> list[Country]:
    """`ACTIVE_COUNTRIES` dagi davlatlar, sozlamadagi tartibda.

    Katalogda yo'q kod jim tashlab ketiladi: bayroq va nomsiz davlatni
    ko'rsatib bo'lmaydi.
    """
    codes = settings.active_country_codes
    if not codes:
        return []
    rows = (
        (await session.execute(select(Country).where(Country.iso_code.in_(codes))))
        .scalars()
        .all()
    )
    by_code = {c.iso_code.upper(): c for c in rows}
    return [by_code[code] for code in codes if code in by_code]


def month_start(now: datetime) -> datetime:
    """Joriy oyning boshlanishi (Toshkent vaqti bo'yicha), UTC'da."""
    local = now.astimezone(TASHKENT_TZ)
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


async def monthly_used(session: AsyncSession, user: User, now: datetime | None = None) -> int:
    """Bu oy nechta savol limitga sanaladi.

    48 soat javobsiz qolgan savol SANALMAYDI: mentorlar band bo'lgani
    uchun foydalanuvchi limitini yo'qotmasligi kerak.
    """
    now = now or now_utc()
    stmt = select(func.count(MentorQuestion.id)).where(
        MentorQuestion.user_id == user.id,
        MentorQuestion.created_at >= month_start(now),
        MentorQuestion.user_notified_48h.is_(False),
    )
    return (await session.execute(stmt)).scalar_one()


async def create_question(
    session: AsyncSession,
    user: User,
    *,
    country_code: str,
    level: MentorLevel,
    topic: MentorTopic,
    text: str,
    now: datetime | None = None,
) -> MentorQuestion:
    code = (country_code or "").strip().upper()
    if code not in settings.active_country_codes:
        raise MentorError("country_inactive")
    body = (text or "").strip()
    if len(body) < QUESTION_MIN_CHARS:
        raise MentorError("text_too_short")
    if len(body) > QUESTION_MAX_CHARS:
        raise MentorError("text_too_long")
    if await monthly_used(session, user, now) >= settings.question_monthly_limit:
        raise MentorError("monthly_limit")

    question = MentorQuestion(
        user_id=user.id,
        country_code=code,
        level=level,
        topic=topic,
        text=body,
        status=MentorQuestionStatus.OPEN,
    )
    if now is not None:
        question.created_at = now
    # Asl savol ham yozishmaning birinchi xabari — chat ekrani va adminka
    # tarixni bitta joydan o'qiydi.
    question.messages.append(MentorMessage(sender=MentorSender.USER, text=body))
    session.add(question)
    await session.flush()
    # Ommaviy raqam bazada (sequence) beriladi.
    await session.refresh(question, attribute_names=["public_number", "created_at"])
    return question


async def get_question(session: AsyncSession, question_id: int) -> MentorQuestion | None:
    stmt = (
        select(MentorQuestion)
        .where(MentorQuestion.id == question_id)
        .options(selectinload(MentorQuestion.messages), selectinload(MentorQuestion.user))
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_user_question(
    session: AsyncSession, user: User, question_id: int
) -> MentorQuestion | None:
    question = await get_question(session, question_id)
    if question is None or question.user_id != user.id:
        return None
    return question


async def list_user_questions(session: AsyncSession, user: User) -> list[MentorQuestion]:
    stmt = (
        select(MentorQuestion)
        .where(MentorQuestion.user_id == user.id)
        .order_by(MentorQuestion.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


# ---------------------------------------------------------------- biriktirish


async def claim(
    session: AsyncSession,
    question_id: int,
    *,
    mentor_tg_id: int,
    mentor_name: str,
    now: datetime | None = None,
) -> MentorQuestion | None:
    """Savolni mentorga biriktiradi. Boshqasi oldin olgan bo'lsa — None.

    Bitta shartli UPDATE: ikkinchi mentorning so'rovi birinchisi commit
    qilinishini kutadi va keyin "status = open" sharti bajarilmay qoladi.
    """
    result = await session.execute(
        update(MentorQuestion)
        .where(
            MentorQuestion.id == question_id,
            MentorQuestion.status == MentorQuestionStatus.OPEN,
        )
        .values(
            status=MentorQuestionStatus.CLAIMED,
            claimed_by_tg_id=mentor_tg_id,
            claimed_by_name=mentor_name[:255],
            claimed_at=now or now_utc(),
            force_reply_message_id=None,
        )
    )
    if result.rowcount != 1:
        return None
    return await get_question(session, question_id)


async def release_claim(session: AsyncSession, question: MentorQuestion) -> bool:
    """Biriktirishni bekor qiladi (12 soat javobsiz yoki mentor chiqib ketdi)."""
    result = await session.execute(
        update(MentorQuestion)
        .where(
            MentorQuestion.id == question.id,
            MentorQuestion.status == MentorQuestionStatus.CLAIMED,
        )
        .values(
            status=MentorQuestionStatus.OPEN,
            claimed_by_tg_id=None,
            claimed_by_name=None,
            claimed_at=None,
            force_reply_message_id=None,
        )
    )
    if result.rowcount != 1:
        return False
    await session.refresh(question)
    return True


async def claimed_by(session: AsyncSession, mentor_tg_id: int) -> list[MentorQuestion]:
    stmt = select(MentorQuestion).where(
        MentorQuestion.status == MentorQuestionStatus.CLAIMED,
        MentorQuestion.claimed_by_tg_id == mentor_tg_id,
    )
    return list((await session.execute(stmt)).scalars().all())


# ---------------------------------------------------------------- javob


async def find_by_force_reply(session: AsyncSession, message_id: int) -> MentorQuestion | None:
    stmt = select(MentorQuestion).where(MentorQuestion.force_reply_message_id == message_id)
    return (await session.execute(stmt)).scalars().first()


def check_answer(
    question: MentorQuestion | None,
    *,
    sender_tg_id: int | None,
    reply_to_message_id: int | None,
    text: str | None,
    allowed_domains: list[str] | None = None,
) -> AnswerVerdict:
    """Guruhdagi xabar javob sifatida qabul qilinadimi.

    Javob = biriktirilgan mentorning AYNAN joriy ForceReply xabariga
    yozgan reply'i. Qolgan hamma narsa (mentorlar suhbati, boshqa savolga
    reply) jim e'tiborsiz qoldiriladi — IGNORE.
    """
    if (
        question is None
        or reply_to_message_id is None
        or question.force_reply_message_id != reply_to_message_id
        or question.status != MentorQuestionStatus.CLAIMED
        or sender_tg_id is None
        or question.claimed_by_tg_id != sender_tg_id
    ):
        return AnswerVerdict.IGNORE
    if text is None:
        return AnswerVerdict.NOT_TEXT
    body = text.strip()
    if len(body) < ANSWER_MIN_CHARS:
        return AnswerVerdict.TOO_SHORT
    domains = settings.allowed_link_domain_list if allowed_domains is None else allowed_domains
    if find_violation(body, domains) is not None:
        return AnswerVerdict.CONTACT
    return AnswerVerdict.OK


async def accept_answer(
    session: AsyncSession,
    question: MentorQuestion,
    *,
    mentor_tg_id: int,
    mentor_name: str,
    text: str,
    now: datetime | None = None,
) -> MentorMessage | None:
    """Javobni yozadi va savolni ANSWERED qiladi. Ikki marta yuborilsa —
    ikkinchisi None (ForceReply allaqachon tozalangan)."""
    now = now or now_utc()
    result = await session.execute(
        update(MentorQuestion)
        .where(
            MentorQuestion.id == question.id,
            MentorQuestion.status == MentorQuestionStatus.CLAIMED,
            MentorQuestion.claimed_by_tg_id == mentor_tg_id,
        )
        .values(
            status=MentorQuestionStatus.ANSWERED,
            answered_at=func.coalesce(MentorQuestion.answered_at, now),
            force_reply_message_id=None,
        )
    )
    if result.rowcount != 1:
        return None
    message = MentorMessage(
        question_id=question.id,
        sender=MentorSender.MENTOR,
        mentor_tg_id=mentor_tg_id,
        mentor_name=mentor_name[:255],
        text=text.strip(),
        created_at=now,
    )
    session.add(message)
    await session.flush()
    await session.refresh(question)
    return message


# ---------------------------------------------------------------- qo'shimcha savol


async def followups_used(session: AsyncSession, question: MentorQuestion) -> int:
    # Birinchi foydalanuvchi xabari — asl savolning o'zi.
    stmt = select(func.count(MentorMessage.id)).where(
        MentorMessage.question_id == question.id,
        MentorMessage.sender == MentorSender.USER,
    )
    return max((await session.execute(stmt)).scalar_one() - 1, 0)


async def add_followup(
    session: AsyncSession,
    question: MentorQuestion,
    user: User,
    text: str,
    now: datetime | None = None,
) -> MentorMessage:
    """Qo'shimcha savolni yozadi va savolni yana o'sha mentorga biriktiradi.

    Mentor guruhdan chiqib ketgan bo'lsa, chaqiruvchi keyin `reopen()` bilan
    savolni umumiy navbatga qaytaradi.
    """
    if question.user_id != user.id:
        raise MentorError("not_found")
    body = (text or "").strip()
    if len(body) < FOLLOWUP_MIN_CHARS:
        raise MentorError("text_too_short")
    if len(body) > QUESTION_MAX_CHARS:
        raise MentorError("text_too_long")
    if question.status != MentorQuestionStatus.ANSWERED:
        raise MentorError("followup_not_allowed")
    if await followups_used(session, question) >= settings.followup_limit:
        raise MentorError("followup_limit")

    now = now or now_utc()
    # Shartli: tugma ikki marta bosilsa ikkinchisi o'tmaydi.
    result = await session.execute(
        update(MentorQuestion)
        .where(
            MentorQuestion.id == question.id,
            MentorQuestion.status == MentorQuestionStatus.ANSWERED,
        )
        .values(
            status=MentorQuestionStatus.CLAIMED,
            claimed_at=now,
            force_reply_message_id=None,
        )
    )
    if result.rowcount != 1:
        raise MentorError("followup_not_allowed")
    message = MentorMessage(
        question_id=question.id, sender=MentorSender.USER, text=body, created_at=now
    )
    session.add(message)
    await session.flush()
    await session.refresh(question)
    return message


async def reopen(session: AsyncSession, question: MentorQuestion) -> None:
    """Savolni umumiy navbatga qaytaradi (mentor yo'q — boshqasi olsin)."""
    await session.execute(
        update(MentorQuestion)
        .where(MentorQuestion.id == question.id)
        .values(
            status=MentorQuestionStatus.OPEN,
            claimed_by_tg_id=None,
            claimed_by_name=None,
            claimed_at=None,
            force_reply_message_id=None,
        )
    )
    await session.refresh(question)


# ---------------------------------------------------------------- yopish va baho


async def close(
    session: AsyncSession, question: MentorQuestion, now: datetime | None = None
) -> bool:
    result = await session.execute(
        update(MentorQuestion)
        .where(
            MentorQuestion.id == question.id,
            MentorQuestion.status != MentorQuestionStatus.CLOSED,
        )
        .values(
            status=MentorQuestionStatus.CLOSED,
            closed_at=now or now_utc(),
            force_reply_message_id=None,
        )
    )
    if result.rowcount != 1:
        return False
    await session.refresh(question)
    return True


async def rate(session: AsyncSession, question: MentorQuestion, user: User, rating: int) -> bool:
    """Bir marta, faqat yopilgan savolga va faqat egasi baholaydi."""
    if not 1 <= rating <= 5:
        raise MentorError("bad_rating")
    result = await session.execute(
        update(MentorQuestion)
        .where(
            MentorQuestion.id == question.id,
            MentorQuestion.user_id == user.id,
            MentorQuestion.status == MentorQuestionStatus.CLOSED,
            MentorQuestion.rating.is_(None),
        )
        .values(rating=rating)
    )
    if result.rowcount != 1:
        return False
    await session.refresh(question)
    return True


# ---------------------------------------------------------------- shikoyat


async def add_complaint(
    session: AsyncSession,
    question: MentorQuestion,
    user: User,
    *,
    reason: ComplaintReason,
    comment: str | None = None,
    message_id: int | None = None,
) -> MentorComplaint:
    if question.user_id != user.id:
        raise MentorError("not_found")
    if message_id is not None:
        # Faqat SHU savoldagi MENTOR xabariga shikoyat qilish mumkin.
        target = await session.get(MentorMessage, message_id)
        if (
            target is None
            or target.question_id != question.id
            or target.sender != MentorSender.MENTOR
        ):
            raise MentorError("bad_message")
    complaint = MentorComplaint(
        question_id=question.id,
        user_id=user.id,
        message_id=message_id,
        reason=reason,
        comment=((comment or "").strip()[:COMMENT_MAX_CHARS] or None),
    )
    session.add(complaint)
    await session.flush()
    return complaint


# ---------------------------------------------------------------- scheduler tanlovlari


async def due_claim_timeouts(session: AsyncSession, now: datetime) -> list[MentorQuestion]:
    stmt = select(MentorQuestion).where(
        MentorQuestion.status == MentorQuestionStatus.CLAIMED,
        MentorQuestion.claimed_at < now - CLAIM_TIMEOUT,
    )
    return list((await session.execute(stmt)).scalars().all())


async def due_group_reminders(session: AsyncSession, now: datetime) -> list[MentorQuestion]:
    stmt = select(MentorQuestion).where(
        MentorQuestion.status == MentorQuestionStatus.OPEN,
        MentorQuestion.answered_at.is_(None),
        MentorQuestion.reminder_24h_sent.is_(False),
        MentorQuestion.created_at < now - REMIND_AFTER,
    )
    return list((await session.execute(stmt)).scalars().all())


async def due_user_notices(session: AsyncSession, now: datetime) -> list[MentorQuestion]:
    stmt = (
        select(MentorQuestion)
        .where(
            MentorQuestion.status.in_(
                (MentorQuestionStatus.OPEN, MentorQuestionStatus.CLAIMED)
            ),
            MentorQuestion.answered_at.is_(None),
            MentorQuestion.user_notified_48h.is_(False),
            MentorQuestion.created_at < now - USER_NOTICE_AFTER,
        )
        .options(selectinload(MentorQuestion.user))
    )
    return list((await session.execute(stmt)).scalars().all())


async def due_auto_close(session: AsyncSession, now: datetime) -> list[MentorQuestion]:
    last_message = (
        select(func.max(MentorMessage.created_at))
        .where(MentorMessage.question_id == MentorQuestion.id)
        .correlate(MentorQuestion)
        .scalar_subquery()
    )
    stmt = (
        select(MentorQuestion)
        .where(
            MentorQuestion.status == MentorQuestionStatus.ANSWERED,
            last_message < now - AUTO_CLOSE_AFTER,
        )
        .options(selectinload(MentorQuestion.user))
    )
    return list((await session.execute(stmt)).scalars().all())
