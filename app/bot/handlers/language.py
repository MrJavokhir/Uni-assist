"""Til tanlash — /start dan keyingi birinchi qadam.

Tartib: /start -> til -> majburiy kanal obunasi -> xush kelibsiz (Mini App
tugmasi). Obuna til tanlangandan KEYIN so'raladi: aks holda odam kanal
so'rovini tushunmaydigan tilda ko'rardi.

Obuna kerak bo'lmasa (kanal qo'shilmagan, foydalanuvchi ozod qilingan yoki
allaqachon a'zo) darhol xush kelibsiz xabari chiqadi. Taklif mukofoti obuna
tasdiqlangan paytda beriladi — shu yerda yoki "A'zo bo'ldim" tugmasida
(app/bot/handlers/subscription.py). U bir martalik, takror chaqirish xavfsiz.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.start import start_keyboard
from app.bot.keyboards import LANGUAGE_CALLBACK_PREFIX, subscription_keyboard
from app.db.models import UiLanguage
from app.i18n import t
from app.services import referral_service
from app.services.redis_client import redis_client
from app.services.subscription_service import missing_channels
from app.services.user_service import get_or_create_user

router = Router(name="language")


@router.callback_query(F.data.startswith(LANGUAGE_CALLBACK_PREFIX))
async def choose_language(callback: CallbackQuery, session: AsyncSession) -> None:
    code = (callback.data or "").removeprefix(LANGUAGE_CALLBACK_PREFIX)
    try:
        ui_language = UiLanguage(code)
    except ValueError:
        await callback.answer()
        return

    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    user.ui_language = ui_language
    await session.commit()

    lang = ui_language.value
    await callback.answer(t("language.saved", lang))

    missing = await missing_channels(callback.bot, session, redis_client, callback.from_user.id)
    if missing:
        await callback.message.edit_text(
            t("subscription.required", lang),
            reply_markup=subscription_keyboard(missing, lang),
        )
        return

    await referral_service.reward_and_notify(session, callback.bot, user)
    await session.commit()

    await callback.message.edit_text(
        t("start.welcome", lang, name=callback.from_user.full_name),
        reply_markup=start_keyboard(lang),
    )
