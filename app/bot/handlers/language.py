"""Til tanlash — /start dan keyingi birinchi qadam.

Til tanlangach darhol Mini App tugmasi beriladi. Majburiy kanal obunasi
bu yerda SO'RALMAYDI: u ilova ichida, filtr orqali qidirishdan oldin
tekshiriladi (app/webapp/api.py, `/subscription`). Taklif mukofoti ham
o'sha yerda — obuna tasdiqlangan paytda — beriladi.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.start import start_keyboard
from app.bot.keyboards import LANGUAGE_CALLBACK_PREFIX
from app.db.models import UiLanguage
from app.i18n import t
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

    await callback.message.edit_text(
        t("start.welcome", lang, name=callback.from_user.full_name),
        reply_markup=start_keyboard(lang),
    )
