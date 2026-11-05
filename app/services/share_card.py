"""Dastur ulashilganda chatga boradigan xabar: karta rasmi, qisqa matn va tugma.

Mini App `Telegram.WebApp.shareMessage()` ni chaqiradi; xabarni esa bot
oldindan tayyorlaydi (`savePreparedInlineMessage`). Xabar uch qismdan iborat:

* **rasm** — Mini App'dagi dastur kartasiga o'xshash: universitet surati,
  chap tepada davlat (bayroq bilan), o'ng tepada ariza muddati, pastda
  logotip, dastur nomi va universitet. Server Pillow bilan chizadi;
* **matn** — daraja, davomiylik, til, muddat, kontrakt va qisqa izoh;
* **tugma** — "Dastur bilan tanishish": dastur sahifasini to'g'ridan-to'g'ri
  ochadigan havola (`p_<id>_r_<telegram_id>` — taklif ham hisoblanadi).

Rasm chizish tashqi rasmlarni yuklab oladi (muqova, logotip, bayroq). Biror
rasm yuklanmasa karta usiz chiziladi — ulashish hech qachon shu sababli
to'xtamaydi.
"""

from __future__ import annotations

import asyncio
import html
import io
import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.db.models.program import INSTRUCTION_LANGUAGES, DeadlineType, Program

logger = logging.getLogger(__name__)

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
CARD_W, CARD_H = 1200, 600
MARGIN = 40
CAPTION_LIMIT = 1024  # Telegram rasm izohi chegarasi

LANGS = ("uz", "ru", "en")

_MONTHS = {
    "uz": [
        "yanvar",
        "fevral",
        "mart",
        "aprel",
        "may",
        "iyun",
        "iyul",
        "avgust",
        "sentyabr",
        "oktyabr",
        "noyabr",
        "dekabr",
    ],
    "ru": [
        "янв.",
        "февр.",
        "мар.",
        "апр.",
        "мая",
        "июн.",
        "июл.",
        "авг.",
        "сент.",
        "окт.",
        "нояб.",
        "дек.",
    ],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

_TEXT = {
    "uz": {
        "closes": "Muddat: {date}",
        "degree": {"bachelor": "Bakalavr", "master": "Magistratura", "phd": "PhD"},
        "years": "yil",
        "tuition": "Kontrakt (yiliga)",
        "free": "Kontrakt: bepul",
        "scholarship": "Dasturning o'z stipendiyasi bor",
        "button": "📖 Dastur bilan tanishish",
    },
    "ru": {
        "closes": "До {date}",
        "degree": {"bachelor": "Бакалавриат", "master": "Магистратура", "phd": "PhD"},
        "years": "г.",
        "tuition": "Контракт (в год)",
        "free": "Обучение бесплатное",
        "scholarship": "Есть собственная стипендия",
        "button": "📖 Подробнее о программе",
    },
    "en": {
        "closes": "Closes {date}",
        "degree": {"bachelor": "Bachelor's", "master": "Master's", "phd": "PhD"},
        "years": "yr",
        "tuition": "Tuition (per year)",
        "free": "Tuition-free",
        "scholarship": "Has its own scholarship",
        "button": "📖 View the program",
    },
}


def _lang(lang: str | None) -> str:
    return lang if lang in LANGS else "uz"


def button_text(lang: str | None) -> str:
    return _TEXT[_lang(lang)]["button"]


def format_short_date(day: date, lang: str | None) -> str:
    lang = _lang(lang)
    month = _MONTHS[lang][day.month - 1]
    if lang == "uz":
        return f"{day.day}-{month}"
    if lang == "ru":
        return f"{day.day} {month}"
    return f"{month} {day.day}"


def next_close_date(program: Program, today: date) -> date | None:
    """Eng yaqin (bugun yoki keyin) ariza yopilish sanasi."""
    closes = sorted(
        d.date_utc.date()
        for d in program.deadlines
        if d.type == DeadlineType.APPLICATION_CLOSE and d.date_utc.date() >= today
    )
    return closes[0] if closes else None


def country_name(program: Program, lang: str | None) -> str:
    country = program.university.country
    lang = _lang(lang)
    return getattr(country, f"name_{lang}", None) or country.name_uz


def _notes(program: Program, lang: str) -> str | None:
    by_lang = {"ru": program.notes_ru, "en": program.notes_en}
    return by_lang.get(lang) or program.notes


def _snippet(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(".,;:—-")
    return f"{cut}…"


def _amount(value: float) -> str:
    return f"{round(value):,}".replace(",", " ")


def build_caption(program: Program, lang: str | None, today: date | None = None) -> str:
    """Rasm ostidagi qisqa matn (HTML)."""
    lang = _lang(lang)
    today = today or datetime.now(UTC).date()
    words = _TEXT[lang]
    def esc(value: str) -> str:
        return html.escape(value, quote=False)
    university = program.university

    duration = float(program.duration_years)
    duration_text = f"{duration:g} {words['years']}"
    language = program.language_of_instruction
    if lang == "uz":
        language = INSTRUCTION_LANGUAGES.get(language, language)
    degree = words["degree"].get(program.degree_level.value, program.degree_level.value)

    lines = [
        f"<b>{esc(program.name)}</b>",
        f"🏛 {esc(university.name)} · {esc(university.city)}, {esc(country_name(program, lang))}",
        "",
        f"🎓 {esc(degree)} · {esc(duration_text)} · {esc(language)}",
    ]
    close = next_close_date(program, today)
    if close:
        lines.append(f"📅 {esc(words['closes'].format(date=format_short_date(close, lang)))}")
    cost = program.cost
    if cost is not None:
        if float(cost.tuition_amount) == 0:
            lines.append(f"💰 {esc(words['free'])}")
        else:
            amount = f"{_amount(float(cost.tuition_amount))} {cost.currency}"
            lines.append(f"💰 {esc(words['tuition'])}: {esc(amount)}")
    if program.has_scholarship:
        lines.append(f"🏅 {esc(words['scholarship'])}")

    caption = "\n".join(lines)
    notes = _notes(program, lang)
    room = CAPTION_LIMIT - len(caption) - 2
    if notes and room > 60:
        # HTML belgilari (&amp; va h.k.) uzunlikni oshiradi — zaxira qoldiriladi.
        caption += "\n\n" + esc(_snippet(notes, min(260, room - 40)))
    return caption


# ---- Rasm ----


@dataclass
class CardData:
    title: str
    university: str
    country: str
    iso_code: str
    deadline: str | None


def card_data(program: Program, lang: str | None, today: date | None = None) -> CardData:
    lang = _lang(lang)
    today = today or datetime.now(UTC).date()
    close = next_close_date(program, today)
    return CardData(
        title=program.name,
        university=program.university.name,
        country=country_name(program, lang),
        iso_code=(program.university.country.iso_code or "").lower(),
        deadline=(
            _TEXT[lang]["closes"].format(date=format_short_date(close, lang)) if close else None
        ),
    )


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS_DIR / f"Inter-{weight}.ttf"), size)


def _open(data: bytes | None) -> Image.Image | None:
    if not data:
        return None
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception:  # noqa: BLE001 — buzuq rasm kartani to'xtatmasin
        logger.warning("Ulashish kartasi: rasmni ochib bo'lmadi")
        return None
    return image


def _background(cover: Image.Image | None) -> Image.Image:
    if cover is not None:
        return ImageOps.fit(cover.convert("RGB"), (CARD_W, CARD_H), Image.Resampling.LANCZOS)
    # Rasm yo'q — brend rangidagi gradient.
    top, bottom = (59, 110, 246), (30, 58, 138)
    gradient = Image.new("RGB", (1, CARD_H))
    for y in range(CARD_H):
        k = y / (CARD_H - 1)
        gradient.putpixel((0, y), tuple(round(a + (b - a) * k) for a, b in zip(top, bottom)))
    return gradient.resize((CARD_W, CARD_H))


def _shade(image: Image.Image) -> None:
    """Pastki qismni qoraytiradi — oq matn har qanday suratda o'qiladi."""
    mask = Image.new("L", (1, CARD_H), 0)
    start = int(CARD_H * 0.30)
    for y in range(start, CARD_H):
        k = (y - start) / (CARD_H - start)
        mask.putpixel((0, y), round(215 * k**1.4))
    image.paste((8, 12, 24), (0, 0), mask.resize((CARD_W, CARD_H)))


def _pill(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
    *,
    flag: Image.Image | None = None,
    align_right: bool = False,
) -> None:
    font = _font("Medium", 34)
    height, pad, gap = 72, 30, 14
    text_w = draw.textlength(text, font=font)
    flag_w = 0
    if flag is not None:
        flag = flag.convert("RGBA")
        flag = flag.resize((round(flag.width * 32 / flag.height), 32), Image.Resampling.LANCZOS)
        flag_w = flag.width + gap
    width = round(pad * 2 + flag_w + text_w)
    if align_right:
        x -= width
    draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2, fill="white")
    cursor = x + pad
    if flag is not None:
        rounded = Image.new("L", flag.size, 0)
        ImageDraw.Draw(rounded).rounded_rectangle((0, 0, *flag.size), radius=5, fill=255)
        alpha = Image.composite(flag.getchannel("A"), rounded, rounded)
        canvas.paste(flag, (cursor, y + (height - flag.height) // 2), alpha)
        cursor += flag_w
    draw.text((cursor, y + height / 2), text, font=font, fill=color, anchor="lm")


def _initials(name: str) -> str:
    words = [w for w in name.replace("-", " ").split() if w[:1].isalpha()]
    skip = {"of", "the", "and", "for", "de", "der", "für"}
    letters = [w[0] for w in words if w.lower() not in skip] or [name[:1] or "U"]
    return "".join(letters[:2]).upper()


def _logo_box(canvas: Image.Image, logo: Image.Image | None, name: str, x: int, y: int) -> None:
    size, radius, inner = 132, 30, 104
    draw = ImageDraw.Draw(canvas)
    usable = logo is not None and min(logo.size) >= 48
    if usable:
        draw.rounded_rectangle((x, y, x + size, y + size), radius=radius, fill="white")
        fitted = ImageOps.contain(logo.convert("RGBA"), (inner, inner), Image.Resampling.LANCZOS)
        offset = (x + (size - fitted.width) // 2, y + (size - fitted.height) // 2)
        canvas.paste(fitted, offset, fitted)
        return
    draw.rounded_rectangle((x, y, x + size, y + size), radius=radius, fill="white")
    draw.rounded_rectangle(
        (x + 8, y + 8, x + size - 8, y + size - 8), radius=radius - 6, fill=(47, 91, 234)
    )
    draw.text(
        (x + size / 2, y + size / 2),
        _initials(name),
        font=_font("Bold", 46),
        fill="white",
        anchor="mm",
    )


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_title(draw: ImageDraw.ImageDraw, text: str, width: int):
    for size in (58, 52, 46, 42):
        font = _font("Bold", size)
        lines = _wrap(draw, text, font, width)
        if len(lines) <= 2:
            return font, lines
    lines = _wrap(draw, text, font, width)
    first, rest = lines[0], " ".join(lines[1:])
    while rest and draw.textlength(f"{rest}…", font=font) > width:
        rest = rest[:-1].rstrip()
    return font, [first, f"{rest}…"]


def _ellipsize(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(f"{text}…", font=font) > width:
        text = text[:-1].rstrip()
    return f"{text}…"


def render_card(
    data: CardData,
    cover: bytes | None = None,
    logo: bytes | None = None,
    flag: bytes | None = None,
) -> bytes:
    """Karta rasmi (JPEG). Sinxron, CPU'ni band qiladi — `asyncio.to_thread` da chaqiring."""
    canvas = _background(_open(cover))
    _shade(canvas)
    draw = ImageDraw.Draw(canvas)

    _pill(draw, canvas, MARGIN, MARGIN, data.country, (17, 24, 39), flag=_open(flag))
    if data.deadline:
        _pill(draw, canvas, CARD_W - MARGIN, MARGIN, data.deadline, (37, 99, 235), align_right=True)

    logo_size = 132
    logo_y = CARD_H - MARGIN - logo_size
    _logo_box(canvas, _open(logo), data.university, MARGIN, logo_y)
    draw = ImageDraw.Draw(canvas)

    text_x = MARGIN + logo_size + 30
    text_w = CARD_W - text_x - MARGIN
    title_font, title_lines = _fit_title(draw, data.title, text_w)
    uni_font = _font("Medium", 34)
    university = _ellipsize(draw, data.university, uni_font, text_w)

    line_h = round(title_font.size * 1.14)
    bottom = CARD_H - MARGIN - 6
    draw.text((text_x, bottom), university, font=uni_font, fill=(214, 220, 230), anchor="ls")
    y = bottom - uni_font.size - 18
    for line in reversed(title_lines):
        draw.text((text_x, y), line, font=title_font, fill="white", anchor="ls")
        y -= line_h

    out = io.BytesIO()
    canvas.save(out, "JPEG", quality=88, optimize=True, progressive=True)
    return out.getvalue()


# ---- Tashqi rasmlarni yuklash va kesh ----

_FETCH_TIMEOUT = aiohttp.ClientTimeout(total=6)
_MAX_IMAGE_BYTES = 8 * 1024 * 1024
_IMAGE_TTL = 24 * 3600
_image_cache: OrderedDict[str, tuple[float, bytes | None]] = OrderedDict()
_IMAGE_CACHE_SIZE = 128


async def fetch_image(url: str | None) -> bytes | None:
    """Tashqi rasm (kesh bilan). Xato bo'lsa None — karta rasmsiz chiziladi."""
    if not url or not url.startswith(("http://", "https://")):
        return None
    cached = _image_cache.get(url)
    if cached and time.monotonic() - cached[0] < _IMAGE_TTL:
        _image_cache.move_to_end(url)
        return cached[1]
    data: bytes | None = None
    try:
        async with (
            aiohttp.ClientSession(
                timeout=_FETCH_TIMEOUT, headers={"User-Agent": "UniAssistBot/1.0"}
            ) as http,
            http.get(url) as response,
        ):
            if response.status == 200:
                body = bytearray()
                async for chunk in response.content.iter_chunked(64 * 1024):
                    body.extend(chunk)
                    if len(body) > _MAX_IMAGE_BYTES:
                        break
                data = bytes(body) if len(body) <= _MAX_IMAGE_BYTES else None
    except Exception:  # noqa: BLE001 — tarmoq xatosi kartani to'xtatmasin
        logger.warning("Ulashish kartasi: rasm yuklanmadi: %s", url)
    _image_cache[url] = (time.monotonic(), data)
    _image_cache.move_to_end(url)
    while len(_image_cache) > _IMAGE_CACHE_SIZE:
        _image_cache.popitem(last=False)
    return data


def flag_url(iso_code: str) -> str | None:
    iso = (iso_code or "").lower()
    return f"https://flagcdn.com/w80/{iso}.png" if len(iso) == 2 and iso.isalpha() else None


_card_cache: OrderedDict[tuple, bytes] = OrderedDict()
_CARD_CACHE_SIZE = 48


async def card_jpeg(
    key: tuple,
    data: CardData,
    load_cover: Callable[[], Awaitable[bytes | None]],
    logo_url: str | None,
) -> bytes:
    """Tayyor karta (jarayon ichida keshlanadi: bir dastur ko'p ulashiladi).

    Muqova faqat keshda yo'q bo'lsa yuklanadi (`load_cover`)."""
    cached = _card_cache.get(key)
    if cached is not None:
        _card_cache.move_to_end(key)
        return cached
    cover, logo, flag = await asyncio.gather(
        load_cover(), fetch_image(logo_url), fetch_image(flag_url(data.iso_code))
    )
    jpeg = await asyncio.to_thread(render_card, data, cover, logo, flag)
    _card_cache[key] = jpeg
    while len(_card_cache) > _CARD_CACHE_SIZE:
        _card_cache.popitem(last=False)
    return jpeg
