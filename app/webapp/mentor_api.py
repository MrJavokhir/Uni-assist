"""Mini App API — "Mentordan so'rash".

Alohida router: `api.py` allaqachon katta, bu esa o'zi alohida funksiya.
Prefiks bir xil (`/api/webapp`), autentifikatsiya ham o'sha
(`get_current_user` — Telegram initData).

Rad etishlar `{"code": "..."}` ko'rinishida qaytadi — Mini App matnni
foydalanuvchi tilida o'zi ko'rsatadi.
"""

import logging
from contextlib import asynccontextmanager
from html import escape

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import (
    ComplaintReason,
    MentorLevel,
    MentorQuestion,
    MentorQuestionStatus,
    MentorSender,
    MentorTopic,
    User,
)
from app.db.session import get_session
from app.services import mentor_group, mentor_service
from app.services.mentor_service import MentorError
from app.webapp.api import get_current_user
from app.webapp.schemas import (
    MentorComplaintIn,
    MentorConfigOut,
    MentorCountryOut,
    MentorMessageOut,
    MentorQuestionIn,
    MentorQuestionOut,
    MentorQuestionSummaryOut,
    MentorRatingIn,
    MentorTextIn,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mentor")


def _reject(code: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code})


@asynccontextmanager
async def _bot():
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        yield bot
    finally:
        await bot.session.close()


def _require_enabled() -> None:
    if not mentor_service.is_enabled():
        raise _reject("disabled", 503)


async def _summary(session: AsyncSession, question: MentorQuestion, lang: str) -> dict:
    country = await mentor_group.get_country(session, question.country_code)
    return {
        "id": question.id,
        "number": question.public_number,
        "country_code": question.country_code,
        "flag": mentor_group.flag(question.country_code),
        "country_name": mentor_group.country_name(country, lang, question.country_code),
        "status": question.status.value,
        "created_at": question.created_at,
    }


async def _question_out(
    session: AsyncSession, question: MentorQuestion, user: User
) -> MentorQuestionOut:
    lang = user.ui_language.value
    used = await mentor_service.followups_used(session, question)
    left = max(settings.followup_limit - used, 0)
    has_mentor_message = any(m.sender == MentorSender.MENTOR for m in question.messages)
    return MentorQuestionOut(
        **(await _summary(session, question, lang)),
        level=question.level.value,
        topic=question.topic.value,
        rating=question.rating,
        messages=[
            MentorMessageOut(
                id=m.id, sender=m.sender.value, text=m.text, created_at=m.created_at
            )
            for m in question.messages
        ],
        followups_left=left,
        can_followup=question.status == MentorQuestionStatus.ANSWERED and left > 0,
        can_close=question.status == MentorQuestionStatus.ANSWERED,
        can_rate=question.status == MentorQuestionStatus.CLOSED
        and question.rating is None
        and has_mentor_message,
        can_complain=has_mentor_message,
    )


async def _load(session: AsyncSession, user: User, question_id: int) -> MentorQuestion:
    question = await mentor_service.get_user_question(session, user, question_id)
    if question is None:
        raise _reject("not_found", 404)
    return question


@router.get("/config", response_model=MentorConfigOut)
async def mentor_config(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> MentorConfigOut:
    lang = user.ui_language.value
    enabled = mentor_service.is_enabled()
    countries = await mentor_service.active_countries(session) if enabled else []
    return MentorConfigOut(
        enabled=enabled and bool(countries),
        countries=[
            MentorCountryOut(
                code=c.iso_code.upper(),
                flag=mentor_group.flag(c.iso_code),
                name=mentor_group.country_name(c, lang),
            )
            for c in countries
        ],
        monthly_limit=settings.question_monthly_limit,
        monthly_used=await mentor_service.monthly_used(session, user),
        followup_limit=settings.followup_limit,
        question_min_chars=mentor_service.QUESTION_MIN_CHARS,
        question_max_chars=mentor_service.QUESTION_MAX_CHARS,
        admin_username=settings.admin_contact_username or None,
    )


@router.get("/questions", response_model=list[MentorQuestionSummaryOut])
async def my_questions(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[MentorQuestionSummaryOut]:
    lang = user.ui_language.value
    return [
        MentorQuestionSummaryOut(**(await _summary(session, q, lang)))
        for q in await mentor_service.list_user_questions(session, user)
    ]


@router.get("/questions/{question_id}", response_model=MentorQuestionOut)
async def get_question(
    question_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MentorQuestionOut:
    return await _question_out(session, await _load(session, user, question_id), user)


@router.post("/questions", response_model=MentorQuestionOut, status_code=201)
async def ask_question(
    payload: MentorQuestionIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MentorQuestionOut:
    _require_enabled()
    try:
        level = MentorLevel(payload.level)
        topic = MentorTopic(payload.topic)
    except ValueError as exc:
        raise _reject("bad_choice") from exc

    try:
        question = await mentor_service.create_question(
            session,
            user,
            country_code=payload.country_code,
            level=level,
            topic=topic,
            text=payload.text,
        )
    except MentorError as exc:
        raise _reject(exc.code) from exc

    # Guruhga tushmagan savolni "yuborildi" deb bo'lmaydi: Telegram xatosida
    # savol bazadan ham qaytariladi va limit yeyilmaydi.
    async with _bot() as bot:
        try:
            await mentor_group.post_question(bot, session, question)
        except Exception as exc:
            await session.rollback()
            logger.exception("Savolni guruhga joylab bo'lmadi")
            raise _reject("send_failed", 502) from exc
    await session.commit()
    return await _question_out(session, await _load(session, user, question.id), user)


@router.post("/questions/{question_id}/followup", response_model=MentorQuestionOut)
async def follow_up(
    question_id: int,
    payload: MentorTextIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MentorQuestionOut:
    _require_enabled()
    question = await _load(session, user, question_id)
    async with _bot() as bot:
        try:
            await mentor_group.submit_followup(bot, session, question, user, payload.text)
        except MentorError as exc:
            await session.rollback()
            raise _reject(exc.code) from exc
        except Exception as exc:
            await session.rollback()
            logger.exception("Qo'shimcha savolni guruhga joylab bo'lmadi")
            raise _reject("send_failed", 502) from exc
    await session.commit()
    return await _question_out(session, await _load(session, user, question_id), user)


@router.post("/questions/{question_id}/close", response_model=MentorQuestionOut)
async def close_question(
    question_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MentorQuestionOut:
    question = await _load(session, user, question_id)
    if question.status != MentorQuestionStatus.ANSWERED:
        raise _reject("close_not_allowed")
    async with _bot() as bot:
        await mentor_group.close_question(bot, session, question, ask_rating=True)
    await session.commit()
    return await _question_out(session, await _load(session, user, question_id), user)


@router.post("/questions/{question_id}/rate", response_model=MentorQuestionOut)
async def rate_question(
    question_id: int,
    payload: MentorRatingIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MentorQuestionOut:
    question = await _load(session, user, question_id)
    try:
        rated = await mentor_service.rate(session, question, user, payload.rating)
    except MentorError as exc:
        raise _reject(exc.code) from exc
    if not rated:
        raise _reject("rate_not_allowed")
    if settings.bot_token and settings.mentor_group_id:
        async with _bot() as bot:
            await mentor_group.after_rating(bot, session, question)
    await session.commit()
    return await _question_out(session, await _load(session, user, question_id), user)


@router.post("/questions/{question_id}/complaints", status_code=201)
async def complain(
    question_id: int,
    payload: MentorComplaintIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    question = await _load(session, user, question_id)
    try:
        reason = ComplaintReason(payload.reason)
    except ValueError as exc:
        raise _reject("bad_choice") from exc
    try:
        complaint = await mentor_service.add_complaint(
            session,
            question,
            user,
            reason=reason,
            comment=payload.comment,
            message_id=payload.message_id,
        )
    except MentorError as exc:
        raise _reject(exc.code) from exc
    await session.commit()

    if settings.bot_token:
        text = (
            f"⚠️ Shikoyat · savol #{question.public_number} · "
            f"{mentor_group.COMPLAINT_LABELS[reason]}"
        )
        if complaint.comment:
            text += f"\n\n{escape(complaint.comment)}"
        async with _bot() as bot:
            await mentor_group.notify_admin(bot, text)
    return {"ok": True}
