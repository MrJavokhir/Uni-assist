from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n import t
from app.services.matching_service import MatchLevel, find_matches
from app.services.user_service import get_or_create_user

router = Router(name="match")

_MISSING_LABELS = {
    "gpa": "GPA",
    "ielts": "IELTS",
}


@router.message(Command("match"))
async def cmd_match(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    lang = user.ui_language.value

    results = await find_matches(session, user)
    visible = [r for r in results if r.level != MatchLevel.RED]

    if not visible:
        await message.answer(t("match.empty", lang))
        return

    green = [r for r in visible if r.level == MatchLevel.GREEN]
    yellow = [r for r in visible if r.level == MatchLevel.YELLOW]

    lines = [t("match.title", lang)]

    if not user.target_countries:
        lines.append(t("match.no_target_countries_hint", lang))

    if green:
        lines.append(t("match.green_header", lang, count=len(green)))
        for r in green:
            lines.append(_format_item(r, lang))

    if yellow:
        lines.append(t("match.yellow_header", lang, count=len(yellow)))
        for r in yellow:
            lines.append(_format_item(r, lang))

    lines.append(t("match.summary", lang, green=len(green), yellow=len(yellow)))

    await message.answer("\n".join(lines))


def _format_item(result, lang: str) -> str:
    program = result.program
    university = program.university
    country = university.country
    line = t(
        "match.item",
        lang,
        program=program.name,
        university=university.name,
        country=country.name_uz,
    )
    if result.missing:
        labels = ", ".join(_MISSING_LABELS.get(m, m) for m in result.missing)
        line += t("match.item_missing", lang, missing=labels)
    return line
