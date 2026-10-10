"""Mentordan so'rash — bot tomoni.

Guruhda:
  * "✋ Javob berish" (`claim:{id}`) — faqat guruh a'zosi, atomik;
  * mentor javobi — biriktirilgan mentorning joriy ForceReply'ga reply'i;
  * a'zo chiqib ketsa (`chat_member`) — uning savollari qayta ochiladi.

Shaxsiy chatda (foydalanuvchi):
  * "✅ Javob oldim" (`close:{id}`) va baho (`rate:{id}:{n}`).

Guruhdagi boshqa xabarlar e'tiborsiz: mentorlar o'zaro gaplashishi mumkin.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.i18n import t
from app.services import mentor_group, mentor_service
from app.services.mentor_service import AnswerVerdict
from app.services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

router = Router(name="mentor")

_VERDICT_REPLIES = {
    AnswerVerdict.NOT_TEXT: "Faqat matnli javob qabul qilinadi.",
    AnswerVerdict.TOO_SHORT: (
        f"Javob juda qisqa — kamida {mentor_service.ANSWER_MIN_CHARS} belgi bo'lsin. "
        "Iltimos, qayta yozing."
    ),
    AnswerVerdict.CONTACT: (
        "Javobda kontakt yoki begona havola bo'lmasligi kerak. Iltimos, qayta yozing."
    ),
}


class InMentorGroup(Filter):
    """Update mentorlar guruhidan keldimi (sozlanmagan bo'lsa — hech qachon)."""

    async def __call__(self, event: TelegramObject) -> bool:
        group_id = settings.mentor_group_id
        if group_id is None:
            return False
        if isinstance(event, CallbackQuery):
            chat = event.message.chat if event.message else None
        else:
            chat = getattr(event, "chat", None)
        return chat is not None and chat.id == group_id


def _parse_id(data: str | None, prefix: str) -> int | None:
    try:
        return int((data or "").removeprefix(prefix).split(":", 1)[0])
    except ValueError:
        return None


@router.callback_query(F.data.startswith(mentor_group.CLAIM_PREFIX), InMentorGroup())
async def on_claim(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    question_id = _parse_id(callback.data, mentor_group.CLAIM_PREFIX)
    if question_id is None:
        await callback.answer()
        return

    mentor = callback.from_user
    is_member, username = await mentor_group.is_group_member(bot, mentor.id)
    if not is_member:
        await callback.answer("Faqat mentorlar javob bera oladi.", show_alert=True)
        return

    question = await mentor_service.claim(
        session, question_id, mentor_tg_id=mentor.id, mentor_name=mentor.full_name
    )
    if question is None:
        await callback.answer("Bu savolni boshqa mentor oldi.", show_alert=True)
        return

    try:
        await mentor_group.after_claim(
            bot,
            session,
            question,
            mentor_tg_id=mentor.id,
            mentor_name=mentor.full_name,
            mentor_username=username or mentor.username,
        )
    except Exception:
        # Biriktirish bekor (rollback) — savol boshqalarga ochiq qoladi.
        await session.rollback()
        logger.exception("Savolni biriktirib bo'lmadi: %s", question_id)
        await callback.answer("Xatolik yuz berdi, qayta urinib ko'ring.", show_alert=True)
        return
    await session.commit()
    await callback.answer("Savol sizga biriktirildi. Javobni ForceReply xabariga yozing.")


@router.message(InMentorGroup())
async def on_group_message(message: Message, session: AsyncSession, bot: Bot) -> None:
    reply = message.reply_to_message
    if reply is None or message.from_user is None:
        return
    question = await mentor_service.find_by_force_reply(session, reply.message_id)
    verdict = mentor_service.check_answer(
        question,
        sender_tg_id=message.from_user.id,
        reply_to_message_id=reply.message_id,
        text=message.text,
    )
    if verdict == AnswerVerdict.IGNORE:
        return
    if verdict != AnswerVerdict.OK:
        # ForceReply amal qilishda davom etadi — mentor shu xabarga qayta yozadi.
        await message.reply(_VERDICT_REPLIES[verdict])
        return

    delivered = await mentor_group.deliver_answer(
        bot,
        session,
        question,
        mentor_tg_id=message.from_user.id,
        mentor_name=message.from_user.full_name,
        text_body=message.text,
        source=message,
    )
    await session.commit()
    if delivered:
        logger.info("Mentor javobi yetkazildi: #%s", question.public_number)


@router.chat_member(InMentorGroup())
async def on_member_update(event: ChatMemberUpdated, session: AsyncSession, bot: Bot) -> None:
    if event.new_chat_member.status not in ("left", "kicked"):
        return
    await mentor_group.release_mentor(bot, session, event.new_chat_member.user.id)
    await session.commit()


@router.callback_query(F.data.startswith(mentor_group.CLOSE_PREFIX))
async def on_close(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value
    question_id = _parse_id(callback.data, mentor_group.CLOSE_PREFIX)
    question = (
        await mentor_service.get_user_question(session, user, question_id)
        if question_id is not None
        else None
    )
    if question is None:
        await callback.answer()
        return

    closed = await mentor_group.close_question(bot, session, question, ask_rating=True)
    await session.commit()
    await callback.answer(t("mentor.closed_toast" if closed else "mentor.already_closed", lang))
    # Javob xabaridagi tugmalar endi kerak emas.
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramAPIError:
        logger.info("Javob xabaridagi tugmalarni olib bo'lmadi")


@router.callback_query(F.data.startswith(mentor_group.RATE_PREFIX))
async def on_rate(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value
    parts = (callback.data or "").removeprefix(mentor_group.RATE_PREFIX).split(":")
    try:
        question_id, rating = int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        await callback.answer()
        return

    question = await mentor_service.get_user_question(session, user, question_id)
    if question is None or not 1 <= rating <= 5:
        await callback.answer()
        return
    if not await mentor_service.rate(session, question, user, rating):
        await callback.answer(t("mentor.already_rated", lang))
        return
    await mentor_group.after_rating(bot, session, question)
    await session.commit()
    await callback.answer()
    try:
        await callback.message.edit_text(t("mentor.rate_thanks", lang, stars="⭐" * rating))
    except TelegramAPIError:
        logger.info("Baho xabarini yangilab bo'lmadi")
