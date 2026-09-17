from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.gpa import format_gpa_result
from app.bot.keyboards import (
    SKIP_CALLBACK,
    countries_keyboard,
    degree_level_keyboard,
    gpa_scale_keyboard,
    lang_cert_type_keyboard,
    skip_only_keyboard,
)
from app.bot.states import ProfileForm
from app.db.models import Country, DegreeLevel, GpaScale, LanguageCertType, UserLanguageCertificate
from app.i18n import t
from app.services.user_service import get_or_create_user, set_target_countries

router = Router(name="profile")


def _today():
    return datetime.now(UTC).date()


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    lang = user.ui_language.value

    await state.clear()
    await state.set_state(ProfileForm.choosing_degree_level)
    await message.answer(t("profile.intro", lang))
    await message.answer(t("profile.degree_level.prompt", lang), reply_markup=degree_level_keyboard(lang))


# --- 1. Daraja (degree level) ---


@router.callback_query(ProfileForm.choosing_degree_level, F.data.startswith("degree:"))
async def choose_degree_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    user.degree_level = DegreeLevel(callback.data.split(":", 1)[1])
    await session.commit()

    await _goto_major(callback.message, state, user.ui_language.value)
    await callback.answer()


async def _goto_major(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ProfileForm.entering_major)
    await message.answer(t("profile.major.prompt", lang), reply_markup=skip_only_keyboard(lang))


# --- 2. Yo'nalish (major) ---


@router.message(ProfileForm.entering_major)
async def enter_major(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    text = (message.text or "").strip()
    if text:
        user.major = text
        await session.commit()

    await _goto_gpa_scale(message, state, user.ui_language.value)


async def _goto_gpa_scale(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ProfileForm.choosing_gpa_scale)
    await message.answer(t("profile.gpa.scale_prompt", lang), reply_markup=gpa_scale_keyboard(lang))


# --- 3-4. GPA (shkala + qiymat) ---


@router.callback_query(ProfileForm.choosing_gpa_scale, F.data.startswith("gpascale:"))
async def choose_gpa_scale(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value
    scale = GpaScale(callback.data.split(":", 1)[1])

    await state.update_data(gpa_scale=scale.value)
    await state.set_state(ProfileForm.entering_gpa_value)
    await callback.message.edit_text(t("profile.gpa.value_prompt", lang), reply_markup=skip_only_keyboard(lang))
    await callback.answer()


@router.message(ProfileForm.entering_gpa_value)
async def enter_gpa_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
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
    scale = GpaScale(data["gpa_scale"])

    user.gpa_raw = value
    user.gpa_scale = scale
    await session.commit()

    await message.answer(format_gpa_result(value, scale, lang))
    await _goto_lang_cert_type(message, state, lang)


async def _goto_lang_cert_type(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ProfileForm.choosing_lang_cert_type)
    await message.answer(t("profile.lang_cert.type_prompt", lang), reply_markup=lang_cert_type_keyboard(lang))


# --- 5-6. Til sertifikati (turi + ball) ---


@router.callback_query(ProfileForm.choosing_lang_cert_type, F.data.startswith("cert:"))
async def choose_lang_cert_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value
    cert_key = callback.data.split(":", 1)[1]

    if cert_key == "none":
        await callback.message.edit_text(t("profile.lang_cert.none", lang))
        await _goto_countries(callback.message, state, session, lang)
        await callback.answer()
        return

    cert_type = LanguageCertType(cert_key)
    await state.update_data(cert_type=cert_type.value)
    await state.set_state(ProfileForm.entering_lang_cert_score)
    cert_name = t(f"profile.lang_cert.{cert_type.value}", lang)
    await callback.message.edit_text(
        t("profile.lang_cert.score_prompt", lang, cert=cert_name),
        reply_markup=skip_only_keyboard(lang),
    )
    await callback.answer()


@router.message(ProfileForm.entering_lang_cert_score)
async def enter_lang_cert_score(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    lang = user.ui_language.value

    try:
        score = float((message.text or "").replace(",", "."))
        if score < 0:
            raise ValueError
    except ValueError:
        await message.answer(t("profile.lang_cert.score_invalid", lang))
        return

    data = await state.get_data()
    cert_type = LanguageCertType(data["cert_type"])

    stmt = select(UserLanguageCertificate).where(
        UserLanguageCertificate.user_id == user.id, UserLanguageCertificate.type == cert_type
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        existing.score = score
    else:
        session.add(
            UserLanguageCertificate(
                user_id=user.id, type=cert_type, score=score, exam_date=_today()
            )
        )
    await session.commit()

    await message.answer(t("common.done", lang))
    await _goto_countries(message, state, session, lang)


# --- 7. Maqsad davlatlar ---


async def _goto_countries(message: Message, state: FSMContext, session: AsyncSession, lang: str) -> None:
    await state.set_state(ProfileForm.choosing_countries)
    await state.update_data(selected_country_ids=[])

    countries = (await session.execute(select(Country).order_by(Country.name_uz))).scalars().all()
    if not countries:
        await message.answer(t("profile.countries.empty", lang))
        await _goto_budget(message, state, lang)
        return

    await message.answer(t("profile.countries.prompt", lang), reply_markup=countries_keyboard(lang, list(countries), set()))


@router.callback_query(ProfileForm.choosing_countries, F.data.startswith("country:"))
async def toggle_country(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value
    country_id = int(callback.data.split(":", 1)[1])

    data = await state.get_data()
    selected: list[int] = list(data.get("selected_country_ids", []))
    if country_id in selected:
        selected.remove(country_id)
    else:
        selected.append(country_id)
    await state.update_data(selected_country_ids=selected)

    countries = (await session.execute(select(Country).order_by(Country.name_uz))).scalars().all()
    await callback.message.edit_reply_markup(
        reply_markup=countries_keyboard(lang, list(countries), set(selected))
    )
    await callback.answer()


@router.callback_query(ProfileForm.choosing_countries, F.data == "countries:done")
async def finish_countries(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value

    data = await state.get_data()
    selected: list[int] = list(data.get("selected_country_ids", []))
    if selected:
        await set_target_countries(session, user, selected)

    await callback.answer()
    await _goto_budget(callback.message, state, lang)


async def _goto_budget(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ProfileForm.entering_budget)
    await message.answer(t("profile.budget.prompt", lang), reply_markup=skip_only_keyboard(lang))


# --- 8. Byudjet ---


@router.message(ProfileForm.entering_budget)
async def enter_budget(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    lang = user.ui_language.value

    try:
        budget = float((message.text or "").replace(",", "").replace("$", ""))
        if budget < 0:
            raise ValueError
    except ValueError:
        await message.answer(t("profile.budget.invalid", lang))
        return

    user.budget_max = budget
    user.budget_currency = "USD"
    await session.commit()

    await _goto_age(message, state, lang)


async def _goto_age(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(ProfileForm.entering_age)
    await message.answer(t("profile.age.prompt", lang), reply_markup=skip_only_keyboard(lang))


# --- 9. Yosh (oxirgi qadam) ---


@router.message(ProfileForm.entering_age)
async def enter_age(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    lang = user.ui_language.value

    try:
        age = int((message.text or "").strip())
        if age <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t("profile.age.invalid", lang))
        return

    user.age = age
    await session.commit()

    await state.clear()
    await message.answer(t("profile.completed", lang))


# --- "Keyin to'ldiraman" — istalgan qadamda ishlaydi ---


@router.callback_query(F.data == SKIP_CALLBACK)
async def skip_step(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value
    current = await state.get_state()

    await callback.answer()

    if current == ProfileForm.choosing_degree_level.state:
        await _goto_major(callback.message, state, lang)
    elif current == ProfileForm.entering_major.state:
        await _goto_gpa_scale(callback.message, state, lang)
    elif current in (ProfileForm.choosing_gpa_scale.state, ProfileForm.entering_gpa_value.state):
        await _goto_lang_cert_type(callback.message, state, lang)
    elif current == ProfileForm.entering_lang_cert_score.state:
        await _goto_countries(callback.message, state, session, lang)
    elif current == ProfileForm.entering_budget.state:
        await _goto_age(callback.message, state, lang)
    elif current == ProfileForm.entering_age.state:
        await state.clear()
        await callback.message.answer(t("profile.completed", lang))
    else:
        await callback.message.answer(t("common.cancelled", lang))
        await state.clear()
