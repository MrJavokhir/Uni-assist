from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.bot.keyboards import (
    LANGUAGE_CALLBACK_PREFIX,
    SUBSCRIPTION_CHECK_CALLBACK,
    subscription_keyboard,
)
from app.db.session import async_session_factory
from app.i18n import t
from app.services.redis_client import redis_client
from app.services.subscription_service import missing_channels
from app.services.user_service import get_or_create_user


class DbSessionMiddleware(BaseMiddleware):
    """Har bir update uchun bitta AsyncSession ochadi va handler'ga `session` sifatida beradi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            return await handler(event, data)


def _is_start_command(message: Message) -> bool:
    """Xabar aynan /start buyrug'imi.

    Deep-link ("/start ref123") va guruh ko'rinishi ("/start@bot") ham
    hisobga olinadi, "/startgroup" kabi boshqa buyruqlar esa yo'q.
    """
    text = (message.text or "").strip()
    if not text.startswith("/start"):
        return False
    command = text.split(maxsplit=1)[0].split("@", 1)[0]
    return command == "/start"


class SubscriptionMiddleware(BaseMiddleware):
    """Majburiy kanal obunasi tekshiruvi.

    Admin panelda faol kanal bo'lmasa — hech narsa qilmaydi. Bo'lsa va
    foydalanuvchi obuna bo'lmagan bo'lsa, handler'ga o'tkazmasdan obuna
    so'rovi xabarini ko'rsatadi.

    Tekshiruvdan ozod: /start buyrug'i hamda til tanlash va "Tekshirish"
    callback'lari. Ular birgalikda "avval til, keyin obuna" tartibini
    ta'minlaydi — obuna so'rovi foydalanuvchi tushunadigan tilda chiqadi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        session = data.get("session")
        bot: Bot | None = data.get("bot")
        if tg_user is None or session is None or bot is None:
            return await handler(event, data)

        # Ikkita callback tekshiruvdan ozod:
        #  - "Tekshirish": aks holda obuna bo'lgan foydalanuvchi o'z holatini
        #    yangilay olmay qolardi;
        #  - til tanlash: obuna so'rovi foydalanuvchi TANLAGAN tilda
        #    ko'rsatilishi uchun avval til saqlanishi kerak.
        raw_event = event.event if hasattr(event, "event") else event
        exempt = (SUBSCRIPTION_CHECK_CALLBACK, LANGUAGE_CALLBACK_PREFIX)
        if isinstance(raw_event, CallbackQuery) and (raw_event.data or "").startswith(exempt):
            return await handler(event, data)

        # /start ham ozod. Birinchi qadam — til tanlash; obuna so'rovi undan
        # keyin, foydalanuvchi TANLAGAN tilda ko'rsatiladi
        # (app/bot/handlers/language.py). Ilgari middleware /start ni ham
        # to'sib qo'yardi va yangi foydalanuvchi til tanlash oynasini umuman
        # ko'rmay, obuna so'rovini standart tilda olardi.
        if isinstance(raw_event, Message) and _is_start_command(raw_event):
            return await handler(event, data)

        missing = await missing_channels(bot, session, redis_client, tg_user.id)
        if not missing:
            return await handler(event, data)

        user = await get_or_create_user(session, tg_user.id, tg_user.username)
        lang = user.ui_language.value
        # Kanal nomlari tugmalarda turibdi — matnda ularni qayta sanab o'tish
        # xabarni ikki marta takrorlangandek ko'rsatardi.
        text = t("subscription.required", lang)
        keyboard = subscription_keyboard(missing, lang)

        if isinstance(raw_event, CallbackQuery):
            await raw_event.answer(t("subscription.short", lang), show_alert=True)
            await raw_event.message.answer(text, reply_markup=keyboard)
        elif isinstance(raw_event, Message):
            await raw_event.answer(text, reply_markup=keyboard)
        return None
