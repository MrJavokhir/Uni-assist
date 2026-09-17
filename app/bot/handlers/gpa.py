from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import gpa_scale_keyboard
from app.bot.states import GpaStandaloneForm
from app.db.models import GpaScale
from app.i18n import t
from app.services.gpa_converter import convert
from app.services.user_service import get_or_create_user

router = Router(name="gpa")


def format_gpa_result(value: float, scale: GpaScale, lang: str) -> str:
    result = convert(value, scale)
    lines = [
        t("profile.gpa.result_title", lang),
        t("profile.gpa.result_us4", lang, value=result.us4),
        t("profile.gpa.result_ects", lang, value=result.ects),
        t("profile.gpa.result_bavarian", lang, value=result.bavarian),
        "",
        t("profile.gpa.disclaimer", lang),
    ]
    return "\n".join(lines)


@router.message(Command("gpa"))
async def cmd_gpa(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    lang = user.ui_language.value
    await state.set_state(GpaStandaloneForm.choosing_scale)
    await message.answer(t("profile.gpa.scale_prompt", lang), reply_markup=gpa_scale_keyboard(lang, skip=False))


@router.callback_query(GpaStandaloneForm.choosing_scale, F.data.startswith("gpascale:"))
async def gpa_choose_scale(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    scale = GpaScale(callback.data.split(":", 1)[1])
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value

    await state.update_data(scale=scale.value)
    await state.set_state(GpaStandaloneForm.entering_value)
    await callback.message.edit_text(t("profile.gpa.value_prompt", lang))
    await callback.answer()


@router.message(GpaStandaloneForm.entering_value)
async def gpa_enter_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    lang = user.ui_language.value

    try:
        value = float((message.text or "").replace(",", "."))
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer(t("profile.gpa.value_invalid", lang))
        return

    data = await state.get_data()
    scale = GpaScale(data["scale"])
    await state.clear()

    await message.answer(format_gpa_result(value, scale, lang))
