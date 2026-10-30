"""Til tanlash tugmalari — endi /start da ko'rsatilmaydi.

/start to'g'ridan-to'g'ri obuna / xush kelibsiz ekraniga o'tadi
(app/bot/handlers/start.py), til Mini App Profil'idan almashtiriladi. Bu
handler chat tarixida qolgan eski til tugmalari bosilganda ishlashi uchun
saqlangan.

Obuna kerak bo'lmasa (kanal qo'shilmagan, foydalanuvchi ozod qilingan yoki
allaqachon a'zo) darhol xush kelibsiz xabari chiqadi. Taklif mukofoti obuna
tasdiqlangan paytda beriladi — shu yerda yoki "A'zo bo'ldim" tugmasida
(app/bot/handlers/subscription.py). U bir martalik, takror chaqirish xavfsiz.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.start import entry_screen
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

    text, markup = await entry_screen(callback.bot, session, user, callback.from_user.full_name)
    await callback.message.edit_text(text, reply_markup=markup)
