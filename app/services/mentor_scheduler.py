"""Mentordan so'rash — davriy tekshiruv (har 30 daqiqada, bot ichida).

| Holat                                   | Harakat                                          |
|-----------------------------------------|--------------------------------------------------|
| claimed, 12 soat javobsiz               | biriktirish bekor, guruhda tugma qaytadi         |
| open, 24 soat javobsiz                  | topic'da eslatma + adminga xabar (bir marta)     |
| open/claimed, 48 soat javobsiz          | foydalanuvchiga xabar (bir marta), limitga sanalmaydi |
| answered, oxirgi xabardan 72 soat       | avtomatik yopiladi + baholash so'raladi          |

Har bir savol alohida commit qilinadi: bittasida Telegram xatosi bo'lsa
qolganlari to'xtab qolmasin. "Bir marta" belgilari bazada, shuning uchun
qayta ishga tushganda xabarlar takrorlanmaydi.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import mentor_group, mentor_service

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 30 * 60


@dataclass
class ScanResult:
    released: int = 0
    reminded: int = 0
    notified: int = 0
    closed: int = 0


def _ids(questions) -> list[int]:
    # Har savol keyin QAYTA yuklanadi: bittasida rollback bo'lsa, ro'yxatdagi
    # qolgan obyektlar eskiradi va async sessiyada ularga tegib bo'lmaydi.
    return [q.id for q in questions]


async def run_mentor_scan(bot: Bot, session: AsyncSession, now: datetime | None = None) -> ScanResult:
    now = now or mentor_service.now_utc()
    result = ScanResult()

    for question_id in _ids(await mentor_service.due_claim_timeouts(session, now)):
        question = await mentor_service.get_question(session, question_id)
        if question is None:
            continue
        try:
            if await mentor_group.release(bot, session, question):
                result.released += 1
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("12 soatlik biriktirishni bekor qilib bo'lmadi: %s", question_id)

    for question_id in _ids(await mentor_service.due_group_reminders(session, now)):
        question = await mentor_service.get_question(session, question_id)
        if question is None:
            continue
        try:
            # Belgi xabar bilan bitta tranzaksiyada: yuborib bo'lmasa rollback
            # bo'ladi va keyingi tekshiruvda qayta urinib ko'riladi.
            question.reminder_24h_sent = True
            question.admin_notified = True
            await session.flush()
            await mentor_group.remind_group(bot, session, question)
            await mentor_group.notify_admin(
                bot,
                f"⏰ Mentor savoli #{question.public_number} "
                f"({mentor_group.flag(question.country_code)} {question.country_code}) "
                "24 soatdan beri javobsiz.",
            )
            await session.commit()
            result.reminded += 1
        except Exception:
            await session.rollback()
            logger.exception("24 soatlik eslatma yuborilmadi: %s", question_id)

    for question_id in _ids(await mentor_service.due_user_notices(session, now)):
        question = await mentor_service.get_question(session, question_id)
        if question is None:
            continue
        try:
            question.user_notified_48h = True
            await session.flush()
            await mentor_group.notify_user_busy(bot, question)
            await session.commit()
            result.notified += 1
        except Exception:
            await session.rollback()
            logger.exception("48 soatlik xabar yuborilmadi: %s", question_id)

    for question_id in _ids(await mentor_service.due_auto_close(session, now)):
        question = await mentor_service.get_question(session, question_id)
        if question is None:
            continue
        try:
            if await mentor_group.close_question(bot, session, question, ask_rating=True, now=now):
                result.closed += 1
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Savolni avtomatik yopib bo'lmadi: %s", question_id)

    return result
