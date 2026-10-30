from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.i18n import t

# Middleware shu prefiksdagi callback'ni obuna tekshiruvidan ozod qiladi.
SUBSCRIPTION_CHECK_CALLBACK = "subcheck"


def subscription_keyboard(channels: list, lang: str) -> InlineKeyboardMarkup:
    """Har bir kanal uchun havola + "Tekshirish" tugmasi."""
    rows = [
        [InlineKeyboardButton(text=f"📢 {channel.title}", url=channel.invite_url)]
        for channel in channels
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text=t("subscription.check_button", lang),
                callback_data=SUBSCRIPTION_CHECK_CALLBACK,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Til tanlash callback'i: "lang:uz" ko'rinishida. /start endi til so'ramaydi —
# faqat chat tarixidagi eski tugmalar uchun. Obuna tekshiruvidan ozod.
LANGUAGE_CALLBACK_PREFIX = "lang:"
