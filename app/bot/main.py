import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import reminders, start
from app.bot.middlewares import DbSessionMiddleware
from app.config import settings
from app.db.session import async_session_factory
from app.services.redis_client import redis_client
from app.services.reminder_service import run_reminder_scan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REMINDER_SCAN_INTERVAL_SECONDS = 3600


def create_dispatcher() -> Dispatcher:
    # Profil kiritish, mos dasturlarni ko'rish va saqlash endi Mini App orqali
    # (app/webapp) amalga oshiriladi — bot faqat uni ochish tugmasini va
    # deadline eslatmalarini (push xabar sifatida) beradi.
    dispatcher = Dispatcher()
    dispatcher.update.middleware(DbSessionMiddleware())

    dispatcher.include_router(start.router)
    dispatcher.include_router(reminders.router)

    return dispatcher


async def reminder_loop(bot: Bot) -> None:
    """Deadline eslatmalarini davriy tekshiradi. Holat DB + Redis'da saqlanadi,
    shuning uchun bot qayta ishga tushirilganda hech narsa yo'qolmaydi yoki takrorlanmaydi."""
    while True:
        try:
            async with async_session_factory() as session:
                sent = await run_reminder_scan(bot, session, redis_client)
                if sent:
                    logger.info("Eslatmalar yuborildi: %s ta", sent)
        except Exception:
            logger.exception("Eslatmalarni tekshirishda xatolik")
        await asyncio.sleep(REMINDER_SCAN_INTERVAL_SECONDS)


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN .env faylida o'rnatilmagan.")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = create_dispatcher()

    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(
        dispatcher.start_polling(bot),
        reminder_loop(bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
