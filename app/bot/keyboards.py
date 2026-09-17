from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import Country, DegreeLevel, GpaScale, LanguageCertType
from app.i18n import t

SKIP_CALLBACK = "skip"


def _with_skip(rows: list[list[InlineKeyboardButton]], lang: str) -> InlineKeyboardMarkup:
    rows.append([InlineKeyboardButton(text=t("common.skip", lang), callback_data=SKIP_CALLBACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="O'zbekcha", callback_data="lang:uz"),
                InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="English", callback_data="lang:en"),
            ]
        ]
    )


def degree_level_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t("profile.degree_level.bachelor", lang), callback_data=f"degree:{DegreeLevel.BACHELOR.value}")],
        [InlineKeyboardButton(text=t("profile.degree_level.master", lang), callback_data=f"degree:{DegreeLevel.MASTER.value}")],
        [InlineKeyboardButton(text=t("profile.degree_level.phd", lang), callback_data=f"degree:{DegreeLevel.PHD.value}")],
    ]
    return _with_skip(rows, lang)


def gpa_scale_keyboard(lang: str, *, skip: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t("profile.gpa.scale_5", lang), callback_data=f"gpascale:{GpaScale.SCALE_5.value}")],
        [InlineKeyboardButton(text=t("profile.gpa.scale_100", lang), callback_data=f"gpascale:{GpaScale.SCALE_100.value}")],
        [InlineKeyboardButton(text=t("profile.gpa.scale_4", lang), callback_data=f"gpascale:{GpaScale.SCALE_4.value}")],
    ]
    if skip:
        return _with_skip(rows, lang)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lang_cert_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=t("profile.lang_cert.IELTS", lang), callback_data=f"cert:{LanguageCertType.IELTS.value}"),
            InlineKeyboardButton(text=t("profile.lang_cert.TOEFL", lang), callback_data=f"cert:{LanguageCertType.TOEFL.value}"),
        ],
        [InlineKeyboardButton(text=t("profile.lang_cert.none", lang), callback_data="cert:none")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def countries_keyboard(lang: str, countries: list[Country], selected_ids: set[int]) -> InlineKeyboardMarkup:
    rows = []
    for country in countries:
        mark = "✅ " if country.id in selected_ids else ""
        rows.append(
            [InlineKeyboardButton(text=f"{mark}{country.name_uz}", callback_data=f"country:{country.id}")]
        )
    rows.append([InlineKeyboardButton(text=t("common.done", lang), callback_data="countries:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_only_keyboard(lang: str) -> InlineKeyboardMarkup:
    return _with_skip([], lang)
