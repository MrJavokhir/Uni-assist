from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SavedProgram
from app.i18n import t
from app.services.user_service import get_or_create_user

router = Router(name="reminders")


@router.callback_query(F.data.startswith("remind_done:"))
async def reminder_done(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value
    saved_id = int(callback.data.split(":", 1)[1])

    stmt = select(SavedProgram).where(SavedProgram.id == saved_id, SavedProgram.user_id == user.id)
    saved = (await session.execute(stmt)).scalar_one_or_none()
    if saved is not None:
        saved.reminders_active = False
        await session.commit()

    await callback.answer(t("reminder.done_confirm", lang), show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("remind_dismiss:"))
async def reminder_dismiss(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value
    saved_id = int(callback.data.split(":", 1)[1])

    stmt = select(SavedProgram).where(SavedProgram.id == saved_id, SavedProgram.user_id == user.id)
    saved = (await session.execute(stmt)).scalar_one_or_none()
    if saved is not None:
        await session.delete(saved)
        await session.commit()

    await callback.answer(t("reminder.dismiss_confirm", lang), show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)
