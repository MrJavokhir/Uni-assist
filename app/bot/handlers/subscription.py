from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.start import start_keyboard
from app.bot.keyboards import SUBSCRIPTION_CHECK_CALLBACK, subscription_keyboard
from app.i18n import t
from app.services.redis_client import redis_client
from app.services.subscription_service import clear_cache, missing_channels
from app.services.user_service import get_or_create_user

router = Router(name="subscription")


@router.callback_query(F.data == SUBSCRIPTION_CHECK_CALLBACK)
async def check_subscription(callback: CallbackQuery, session: AsyncSession) -> None:
    """Foydalanuvchi "Tekshirish" tugmasini bosganda obunani qayta tekshiradi."""
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value

    # Kesh tozalanadi: foydalanuvchi hozirgina obuna bo'lgan bo'lishi mumkin.
    await clear_cache(redis_client, callback.from_user.id)
    missing = await missing_channels(
        callback.bot, session, redis_client, callback.from_user.id, use_cache=False
    )

    if missing:
        await callback.answer(t("subscription.still_missing", lang), show_alert=True)
        await callback.message.edit_reply_markup(
            reply_markup=subscription_keyboard(missing, lang)
        )
        return

    await callback.answer(t("subscription.thanks", lang))
    await callback.message.edit_text(
        t("start.welcome", lang, name=callback.from_user.full_name),
        reply_markup=start_keyboard(lang),
    )
