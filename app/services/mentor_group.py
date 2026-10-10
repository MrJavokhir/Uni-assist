"""Mentordan so'rash — Telegram tomoni.

Bu yerda guruh, topic'lar va foydalanuvchiga yetkazish. Qaror va holat
`mentor_service.py` da; bu modul ularni Telegram harakatlariga ulaydi.

Telegram xatolari holatni BUZMASLIGI kerak: xabarni tahrirlab bo'lmasa
(o'chirilgan, "not modified") — jim o'tamiz, chunki asosiy manba baza.
Faqat SAVOLNI JOYLASH muvaffaqiyatsiz bo'lsa xato chaqiruvchiga qaytadi:
guruhga tushmagan savolni "yuborildi" deb ko'rsatib bo'lmaydi.

Maxfiylik:
  * guruhga boradigan matnda foydalanuvchi haqida hech narsa yo'q
    (faqat raqam, davlat, daraja, mavzu va savol matni);
  * foydalanuvchiga boradigan matnda mentor faqat "{davlat}dagi mentor".
"""

import logging
from datetime import datetime
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReactionTypeEmoji,
    ReplyParameters,
    WebAppInfo,
)
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import (
    ComplaintReason,
    Country,
    CountryTopic,
    MentorLevel,
    MentorQuestion,
    MentorQuestionStatus,
    MentorTopic,
    User,
)
from app.i18n import t
from app.services import mentor_service

logger = logging.getLogger(__name__)

CLAIM_PREFIX = "claim:"
CLOSE_PREFIX = "close:"
RATE_PREFIX = "rate:"

LEVEL_LABELS = {MentorLevel.BACHELOR: "Bakalavr", MentorLevel.MASTER: "Magistratura"}
TOPIC_LABELS = {
    MentorTopic.ADMISSION: "🎯 Kirish",
    MentorTopic.DOCUMENTS: "📄 Hujjatlar",
    MentorTopic.VISA: "🛂 Viza",
    MentorTopic.LIVING: "🏠 Yashash va xarajatlar",
    MentorTopic.WORK: "💼 Ish",
    MentorTopic.STUDIES: "📚 O'qish jarayoni",
    MentorTopic.OTHER: "💬 Boshqa",
}

# Admin uchun (Telegram ogohlantirishi va adminka).
COMPLAINT_LABELS = {
    ComplaintReason.WRONG_INFO: "Noto'g'ri ma'lumot",
    ComplaintReason.DISRESPECT: "Hurmatsiz muomala",
    ComplaintReason.PAID_OR_AD: "Pullik xizmat yoki reklama",
    ComplaintReason.OTHER: "Boshqa",
}


# ---------------------------------------------------------------- yordamchilar


def flag(code: str) -> str:
    """ISO kod -> bayroq emoji ("DE" -> 🇩🇪)."""
    code = (code or "").upper()
    if len(code) != 2 or not code.isalpha():
        return "🏳️"
    return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in code)


def country_name(country: Country | None, lang: str = "uz", code: str = "") -> str:
    if country is None:
        return code
    return getattr(country, f"name_{lang}", None) or country.name_uz


async def get_country(session: AsyncSession, code: str) -> Country | None:
    stmt = select(Country).where(Country.iso_code == code.upper())
    return (await session.execute(stmt)).scalar_one_or_none()


def webapp_link(path: str) -> WebAppInfo | None:
    # `WebAppInfo` `startapp` ni qabul qilmaydi — parametr URL'ning
    # o'ziga qo'shiladi, Mini App uni `location.hash` dan o'qiydi
    # (deadline eslatmalaridagi bilan bir xil yo'l).
    base = (settings.webapp_url or "").rstrip("/")
    return WebAppInfo(url=f"{base}/#{path}") if base else None


def mention(tg_id: int, name: str, username: str | None = None) -> str:
    if username:
        return f"@{escape(username)}"
    return f'<a href="tg://user?id={tg_id}">{escape(name or "Mentor")}</a>'


def _group_id() -> int:
    if settings.mentor_group_id is None:
        raise RuntimeError("MENTOR_GROUP_ID sozlanmagan")
    return settings.mentor_group_id


def status_line(question: MentorQuestion) -> str:
    name = escape(question.claimed_by_name or "mentor")
    if question.status == MentorQuestionStatus.CLAIMED:
        return f"✋ {name} javob bermoqda"
    if question.status == MentorQuestionStatus.ANSWERED:
        return f"✅ Javob berildi · {name}"
    if question.status == MentorQuestionStatus.CLOSED:
        rating = f" · ⭐ {question.rating}" if question.rating else ""
        return f"🔒 Yopildi{rating}"
    return ""


def question_html(question: MentorQuestion, country: Country | None) -> str:
    """Guruhdagi savol xabari. Foydalanuvchi haqida HECH NARSA yo'q."""
    head = (
        f"❓ <b>Savol #{question.public_number}</b> · {flag(question.country_code)} "
        f"{escape(country_name(country, 'uz', question.country_code))}\n"
        f"🎓 {LEVEL_LABELS[question.level]} · {TOPIC_LABELS[question.topic]}\n\n"
        f"{escape(question.text)}"
    )
    line = status_line(question)
    return f"{head}\n\n{line}" if line else head


def claim_keyboard(question: MentorQuestion) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✋ Javob berish", callback_data=f"{CLAIM_PREFIX}{question.id}"
                )
            ]
        ]
    )


def rating_keyboard(question: MentorQuestion) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=str(n), callback_data=f"{RATE_PREFIX}{question.id}:{n}"
                )
                for n in range(1, 6)
            ]
        ]
    )


def answer_keyboard(question: MentorQuestion, lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    app_link = webapp_link(f"question_{question.id}")
    if app_link is not None:
        rows.append(
            [InlineKeyboardButton(text=t("mentor.btn_followup", lang), web_app=app_link)]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("mentor.btn_close", lang),
                callback_data=f"{CLOSE_PREFIX}{question.id}",
            )
        ]
    )
    if app_link is not None:
        rows.append(
            [InlineKeyboardButton(text=t("mentor.btn_complain", lang), web_app=app_link)]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def is_group_member(bot: Bot, tg_id: int) -> tuple[bool, str | None]:
    """(a'zomi, username). Tekshirib bo'lmasa — a'zo emas deb hisoblanadi:
    javob berish huquqi xato bilan berilmasligi kerak."""
    try:
        member = await bot.get_chat_member(_group_id(), tg_id)
    except TelegramAPIError:
        logger.exception("Mentor a'zoligini tekshirib bo'lmadi: %s", tg_id)
        return False, None
    return member.status in mentor_service.MEMBER_STATUSES, member.user.username


# ---------------------------------------------------------------- topic'lar


def _topic_gone(err: TelegramBadRequest) -> bool:
    message = (err.message or "").lower()
    return any(
        marker in message
        for marker in ("thread not found", "topic_deleted", "topic_id_invalid", "topic not found")
    )


async def ensure_topic(bot: Bot, session: AsyncSession, code: str) -> int:
    """Davlat topic'i; yo'q bo'lsa yaratiladi.

    Advisory lock: bir vaqtda kelgan ikki savol ikkita topic ochib
    qo'ymasligi uchun. Qulf tranzaksiya tugaguncha turadi.
    """
    code = code.upper()
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"mentor_topic:{code}"}
    )
    row = await session.get(CountryTopic, code, populate_existing=True)
    if row is not None:
        return row.message_thread_id

    country = await get_country(session, code)
    name = f"{flag(code)} {country_name(country, 'uz', code)}"
    topic = await bot.create_forum_topic(_group_id(), name[:128])
    session.add(CountryTopic(country_code=code, message_thread_id=topic.message_thread_id))
    await session.flush()
    logger.info("Mentor topic yaratildi: %s -> %s", code, topic.message_thread_id)
    return topic.message_thread_id


async def forget_topic(session: AsyncSession, code: str) -> None:
    await session.execute(delete(CountryTopic).where(CountryTopic.country_code == code.upper()))
    await session.flush()


async def send_in_topic(
    bot: Bot,
    session: AsyncSession,
    code: str,
    html: str,
    *,
    reply_markup=None,
    reply_to: int | None = None,
) -> Message:
    """Davlat topic'iga yuboradi. Topic o'chirilgan bo'lsa — yozuv
    o'chiriladi, topic qayta yaratiladi va xabar qayta yuboriladi."""
    for attempt in range(2):
        thread_id = await ensure_topic(bot, session, code)
        try:
            return await bot.send_message(
                _group_id(),
                html,
                message_thread_id=thread_id,
                reply_markup=reply_markup,
                reply_parameters=(
                    ReplyParameters(message_id=reply_to, allow_sending_without_reply=True)
                    if reply_to
                    else None
                ),
            )
        except TelegramBadRequest as err:
            if attempt == 0 and _topic_gone(err):
                logger.warning("Mentor topic topilmadi, qayta yaratiladi: %s", code)
                await forget_topic(session, code)
                continue
            raise
    raise RuntimeError("unreachable")


async def _edit_group_message(
    bot: Bot, session: AsyncSession, question: MentorQuestion, *, with_button: bool
) -> None:
    if not question.group_message_id:
        return
    country = await get_country(session, question.country_code)
    try:
        await bot.edit_message_text(
            question_html(question, country),
            chat_id=_group_id(),
            message_id=question.group_message_id,
            reply_markup=claim_keyboard(question) if with_button else None,
        )
    except TelegramAPIError as err:
        # "message is not modified" yoki xabar o'chirilgan — baza baribir to'g'ri.
        logger.info("Guruhdagi savol xabarini tahrirlab bo'lmadi (#%s): %s",
                    question.public_number, err)


async def _delete_quietly(bot: Bot, message_id: int | None) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(_group_id(), message_id)
    except TelegramAPIError:
        pass


async def _send_user(bot: Bot, user: User, html: str, markup=None) -> bool:
    try:
        await bot.send_message(user.telegram_id, html, reply_markup=markup)
    except TelegramForbiddenError:
        logger.info("Foydalanuvchi botni bloklagan: %s", user.telegram_id)
        return False
    except TelegramAPIError:
        logger.exception("Foydalanuvchiga mentor xabari yetmadi: %s", user.telegram_id)
        return False
    return True


async def notify_admin(bot: Bot, html: str) -> None:
    if not settings.admin_telegram_id:
        return
    try:
        await bot.send_message(settings.admin_telegram_id, html)
    except TelegramAPIError:
        logger.exception("Adminga mentor ogohlantirishi yetmadi")


# ---------------------------------------------------------------- oqimlar


async def post_question(bot: Bot, session: AsyncSession, question: MentorQuestion) -> None:
    """Yangi savolni topic'ga "Javob berish" tugmasi bilan joylaydi."""
    country = await get_country(session, question.country_code)
    message = await send_in_topic(
        bot,
        session,
        question.country_code,
        question_html(question, country),
        reply_markup=claim_keyboard(question),
    )
    question.group_message_id = message.message_id
    await session.flush()


async def ask_for_answer(
    bot: Bot,
    session: AsyncSession,
    question: MentorQuestion,
    *,
    mentor_tg_id: int,
    mentor_name: str,
    mentor_username: str | None,
    reply_to: int | None,
) -> None:
    """Mentorga ForceReply: javob AYNAN shu xabarga reply bo'lishi kerak."""
    who = mention(mentor_tg_id, mentor_name, mentor_username)
    message = await send_in_topic(
        bot,
        session,
        question.country_code,
        f"{who}, savol #{question.public_number} ga javobingizni shu xabarga reply qilib yozing.",
        reply_markup=ForceReply(
            force_reply=True, selective=True, input_field_placeholder="Javobingiz..."
        ),
        reply_to=reply_to,
    )
    question.force_reply_message_id = message.message_id
    await session.flush()


async def after_claim(
    bot: Bot,
    session: AsyncSession,
    question: MentorQuestion,
    *,
    mentor_tg_id: int,
    mentor_name: str,
    mentor_username: str | None,
) -> None:
    await _edit_group_message(bot, session, question, with_button=False)
    await ask_for_answer(
        bot,
        session,
        question,
        mentor_tg_id=mentor_tg_id,
        mentor_name=mentor_name,
        mentor_username=mentor_username,
        reply_to=question.group_message_id,
    )


async def deliver_answer(
    bot: Bot,
    session: AsyncSession,
    question: MentorQuestion,
    *,
    mentor_tg_id: int,
    mentor_name: str,
    text_body: str,
    source: Message | None = None,
    now: datetime | None = None,
) -> bool:
    """Javobni qabul qiladi va foydalanuvchiga anonim yetkazadi."""
    message = await mentor_service.accept_answer(
        session,
        question,
        mentor_tg_id=mentor_tg_id,
        mentor_name=mentor_name,
        text=text_body,
        now=now,
    )
    if message is None:
        return False

    user = await session.get(User, question.user_id)
    country = await get_country(session, question.country_code)
    if user is not None:
        lang = user.ui_language.value
        await _send_user(
            bot,
            user,
            t(
                "mentor.answer_received",
                lang,
                country=escape(country_name(country, lang, question.country_code)),
                number=question.public_number,
                answer=escape(message.text),
            ),
            answer_keyboard(question, lang),
        )

    await _edit_group_message(bot, session, question, with_button=False)
    if source is not None:
        await _confirm_sent(bot, source)
    return True


async def _confirm_sent(bot: Bot, source: Message) -> None:
    # "✅" Telegram reaksiyalari ro'yxatida yo'q — eng yaqini 👌. U ham
    # bo'lmasa (guruhda reaksiyalar o'chirilgan) qisqa reply.
    try:
        await bot.set_message_reaction(
            source.chat.id, source.message_id, reaction=[ReactionTypeEmoji(emoji="👌")]
        )
        return
    except TelegramAPIError:
        pass
    try:
        await source.reply("✅ Yuborildi")
    except TelegramAPIError:
        logger.info("Javob tasdig'ini yuborib bo'lmadi")


async def submit_followup(
    bot: Bot,
    session: AsyncSession,
    question: MentorQuestion,
    user: User,
    text_body: str,
    now: datetime | None = None,
) -> None:
    """Qo'shimcha savol. Mentor guruhda bo'lsa — unga ForceReply bilan,
    chiqib ketgan bo'lsa — umumiy navbatga "Javob berish" tugmasi bilan."""
    mentor_tg_id = question.claimed_by_tg_id
    mentor_name = question.claimed_by_name or "Mentor"
    message = await mentor_service.add_followup(session, question, user, text_body, now)

    in_group, username = (False, None)
    if mentor_tg_id is not None:
        in_group, username = await is_group_member(bot, mentor_tg_id)

    body = (
        f"↪️ Savol #{question.public_number} bo'yicha qo'shimcha savol:\n"
        f"{escape(message.text)}"
    )
    if in_group:
        posted = await send_in_topic(
            bot, session, question.country_code, body, reply_to=question.group_message_id
        )
        await ask_for_answer(
            bot,
            session,
            question,
            mentor_tg_id=mentor_tg_id,
            mentor_name=mentor_name,
            mentor_username=username,
            reply_to=posted.message_id,
        )
        return

    # Mentor yo'q — savol boshqa mentorlarga ochiladi. Eski xabardagi holat
    # ("Javob berildi") qoladi; yangi xabar asl savol bilan birga chiqadi,
    # chunki yangi mentor oldingi yozishmani ko'rmagan.
    await mentor_service.reopen(session, question)
    country = await get_country(session, question.country_code)
    posted = await send_in_topic(
        bot,
        session,
        question.country_code,
        f"{body}\n\n— — —\n{question_html(question, country)}",
        reply_markup=claim_keyboard(question),
        reply_to=question.group_message_id,
    )
    question.group_message_id = posted.message_id
    await session.flush()


async def close_question(
    bot: Bot,
    session: AsyncSession,
    question: MentorQuestion,
    *,
    ask_rating: bool,
    now: datetime | None = None,
) -> bool:
    force_reply = question.force_reply_message_id
    if not await mentor_service.close(session, question, now):
        return False
    await _delete_quietly(bot, force_reply)
    await _edit_group_message(bot, session, question, with_button=False)
    if ask_rating:
        user = await session.get(User, question.user_id)
        if user is not None:
            lang = user.ui_language.value
            await _send_user(
                bot,
                user,
                t("mentor.rate_prompt", lang, number=question.public_number),
                rating_keyboard(question),
            )
    return True


async def after_rating(bot: Bot, session: AsyncSession, question: MentorQuestion) -> None:
    await _edit_group_message(bot, session, question, with_button=False)


async def release(bot: Bot, session: AsyncSession, question: MentorQuestion) -> bool:
    """Biriktirishni bekor qiladi va guruhda tugmani qaytaradi."""
    force_reply = question.force_reply_message_id
    if not await mentor_service.release_claim(session, question):
        return False
    await _delete_quietly(bot, force_reply)
    await _edit_group_message(bot, session, question, with_button=True)
    return True


async def release_mentor(bot: Bot, session: AsyncSession, mentor_tg_id: int) -> int:
    """Mentor guruhdan chiqdi — unga biriktirilgan savollar qayta ochiladi."""
    count = 0
    for question in await mentor_service.claimed_by(session, mentor_tg_id):
        if await release(bot, session, question):
            count += 1
    if count:
        logger.info("Mentor %s chiqdi, %s ta savol qayta ochildi", mentor_tg_id, count)
    return count


async def remind_group(bot: Bot, session: AsyncSession, question: MentorQuestion) -> None:
    await send_in_topic(
        bot,
        session,
        question.country_code,
        f"⏰ Savol #{question.public_number} hali javobsiz",
        reply_to=question.group_message_id,
    )


async def notify_user_busy(bot: Bot, question: MentorQuestion) -> None:
    user = question.user
    lang = user.ui_language.value
    await _send_user(bot, user, t("mentor.busy_48h", lang, number=question.public_number))
