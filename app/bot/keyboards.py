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


# Til tanlash callback'i: "lang:uz" ko'rinishida. Obuna tekshiruvidan ozod —
# foydalanuvchi hali tilni tanlamasdan turib kanal so'rovini ko'rmasligi kerak.
LANGUAGE_CALLBACK_PREFIX = "lang:"

LANGUAGE_CHOICES = (
    ("uz", "🇺🇿 O'zbekcha"),
    ("ru", "🇷🇺 Русский"),
    ("en", "🇬🇧 English"),
)


def language_keyboard() -> InlineKeyboardMarkup:
    """Til tanlash — har bir til alohida qatorda, bayrog'i bilan."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"{LANGUAGE_CALLBACK_PREFIX}{code}")]
            for code, label in LANGUAGE_CHOICES
        ]
    )
