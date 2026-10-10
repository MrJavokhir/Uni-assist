import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.handlers import language, mentor, payment, reminders, start, subscription
from app.bot.middlewares import DbSessionMiddleware
from app.bot.profile_setup import apply_bot_profile
from app.config import settings
from app.db.session import async_session_factory
from app.services import mentor_service
from app.services.mentor_scheduler import SCAN_INTERVAL_SECONDS, run_mentor_scan
from app.services.redis_client import redis_client
from app.services.reminder_service import is_send_time, run_reminder_scan
from app.services.timezone_utils import TASHKENT_TZ

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Har yarim soatda uyg'onamiz, lekin xabar faqat Toshkent vaqti bilan
# 10:00 da ketadi. Tez-tez uyg'onish kerak: konteyner istalgan paytda
# qayta ishga tushadi va aniq 10:00 ga tushishi shart emas.
REMINDER_TICK_SECONDS = 1800
# Kunlik qulf: deploy paytidagi eski va yangi konteyner bir kunda ikki
# marta yubormasligi uchun. Redis'da, chunki jarayon xotirasi buni
# kafolatlay olmaydi.
_DAILY_LOCK_TTL_SECONDS = 23 * 3600


def create_dispatcher() -> Dispatcher:
    # Profil kiritish, mos dasturlarni ko'rish va saqlash endi Mini App orqali
    # (app/webapp) amalga oshiriladi — bot faqat uni ochish tugmasini va
    # deadline eslatmalarini (push xabar sifatida) beradi.
    # FSM holati Redis'da: to'lov oqimi bir necha xabardan iborat, konteyner
    # esa har deployda qayta ishga tushadi. Xotiradagi holat yo'qolib,
    # foydalanuvchi summani kiritgandan keyin "osilib" qolardi.
    dispatcher = Dispatcher(storage=RedisStorage(redis_client))
    # Majburiy kanal obunasi botda TEKSHIRILMAYDI — u Mini App'da, filtr
    # orqali qidirishdan oldin so'raladi (app/webapp/api.py, `/subscription`).
    dispatcher.update.middleware(DbSessionMiddleware())

    # Mentor router BIRINCHI: mentorlar guruhidagi har qanday xabar shu
    # yerda tugaydi va shaxsiy chat uchun yozilgan handler'larga (to'lov,
    # /start) tushib qolmaydi.
    dispatcher.include_router(mentor.router)
    dispatcher.include_router(language.router)
    dispatcher.include_router(payment.router)
    dispatcher.include_router(subscription.router)
    dispatcher.include_router(start.router)
    dispatcher.include_router(reminders.router)

    return dispatcher


async def _claim_today(today_iso: str) -> bool:
    """Bugungi yuborishni shu nusxa bajaradimi.

    `SET key value NX` atomar ishlaydi: bir vaqtda ishlayotgan nusxalardan
    faqat bittasi True oladi.
    """
    return bool(
        await redis_client.set(
            f"reminder_daily:{today_iso}", "1", nx=True, ex=_DAILY_LOCK_TTL_SECONDS
        )
    )


async def reminder_loop(bot: Bot) -> None:
    """Kuniga bir marta, Toshkent vaqti bilan 10:00 da eslatmalarni yuboradi.

    Holat butunlay bazada (`notification_logs`), shuning uchun bot qayta ishga
    tushirilganda xabarlar na yo'qoladi, na takrorlanadi.
    """
    while True:
        try:
            now = datetime.now(TASHKENT_TZ)
            if is_send_time(now) and await _claim_today(now.date().isoformat()):
                async with async_session_factory() as session:
                    result = await run_reminder_scan(bot, session)
                logger.info(
                    "Eslatmalar: %s foydalanuvchiga, %s dastur bo'yicha (bloklangan: %s)",
                    result.sent_users,
                    result.sent_messages,
                    result.blocked_users,
                )
        except Exception:
            logger.exception("Eslatmalarni tekshirishda xatolik")
        await asyncio.sleep(REMINDER_TICK_SECONDS)

async def mentor_loop(bot: Bot) -> None:
    """Mentor savollarini har 30 daqiqada tekshiradi (12/24/48/72 soat).

    Redis qulfi: deploy paytida eski va yangi konteyner bir vaqtda
    ishlasa, tekshiruvni faqat bittasi bajaradi.
    """
    while True:
        try:
            if mentor_service.is_enabled() and await redis_client.set(
                "mentor_scan_lock", "1", nx=True, ex=SCAN_INTERVAL_SECONDS - 60
            ):
                async with async_session_factory() as session:
                    result = await run_mentor_scan(bot, session)
                if any(vars(result).values()):
                    logger.info("Mentor tekshiruvi: %s", result)
        except Exception:
            logger.exception("Mentor savollarini tekshirishda xatolik")
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN .env faylida o'rnatilmagan.")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = create_dispatcher()

    await bot.delete_webhook(drop_pending_updates=True)
    # Bo'sh suhbatda ko'rinadigan tavsif. Pollingdan OLDIN: bu bir martalik
    # qisqa amal va u tugamasdan xabar qabul qilishning ma'nosi yo'q.
    await apply_bot_profile(bot)
    await asyncio.gather(
        # `chat_member` Telegram'da standart holatda YUBORILMAYDI — ro'yxat
        # aniq beriladi (mentor guruhdan chiqqanini bilish uchun kerak).
        dispatcher.start_polling(
            bot, allowed_updates=dispatcher.resolve_used_update_types()
        ),
        reminder_loop(bot),
        mentor_loop(bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
