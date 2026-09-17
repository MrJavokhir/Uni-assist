import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import gpa, match, profile, start
from app.bot.middlewares import DbSessionMiddleware
from app.config import settings

logging.basicConfig(level=logging.INFO)


def create_dispatcher() -> Dispatcher:
    # MVP uchun MemoryStorage — bot qayta ishga tushsa FSM holati yo'qoladi,
    # lekin profil bazada (User jadvalida) saqlanadi, shu sababli ma'lumot yo'qolmaydi.
    # Eslatmalar navbati (3-bosqich) uchun Redis alohida ishlatiladi.
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.middleware(DbSessionMiddleware())

    dispatcher.include_router(start.router)
    dispatcher.include_router(profile.router)
    dispatcher.include_router(gpa.router)
    dispatcher.include_router(match.router)

    return dispatcher


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN .env faylida o'rnatilmagan.")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = create_dispatcher()

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
