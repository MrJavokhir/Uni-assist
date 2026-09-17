from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import language_keyboard
from app.db.models import UiLanguage
from app.i18n import t
from app.services.user_service import get_or_create_user

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t("start.choose_language"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, session: AsyncSession) -> None:
    lang = callback.data.split(":", 1)[1]
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    user.ui_language = UiLanguage(lang)
    await session.commit()

    await callback.message.edit_text(t("start.welcome", lang, name=callback.from_user.full_name))
    await callback.answer()
