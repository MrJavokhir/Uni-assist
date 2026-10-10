"""Mentor javobidagi kontakt va begona havolalarni ushlash.

Maqsad — foydalanuvchi va mentor bot'ni chetlab, to'g'ridan-to'g'ri
bog'lanib ketmasligi (pullik "konsultatsiya", reklama). Shuning uchun:

  * telefon raqami, @username va Telegram havolasi — HAR DOIM taqiqlangan;
  * boshqa havolalar va e-pochta — faqat `ALLOWED_LINK_DOMAINS` dagi
    domenlarda ruxsat (universitet, DAAD kabi rasmiy saytlar foydali).

Filtr mukammal emas va bo'lishi ham shart emas: maqsad tasodifiy va
ochiq-oydin urinishlarni to'xtatish. Qolganini shikoyat tizimi ushlaydi.
"""

import enum
import re


class Violation(str, enum.Enum):
    PHONE = "phone"
    USERNAME = "username"
    TELEGRAM_LINK = "telegram_link"
    LINK = "link"
    EMAIL = "email"


# Raqamlar ketma-ketligi (oraliq belgilar bilan). Telefon deb hisoblash uchun
# kamida 9 ta raqam kerak: "1 200 000 so'm" yoki "2024-2025" o'tib ketsin,
# "90 123 45 67" esa ushlansin. "+" bilan boshlangani — 7 tadan.
_DIGIT_RUN = re.compile(r"\+?\d[\d\s().\-]{5,}\d")
_PHONE_MIN_DIGITS = 9
_PLUS_PHONE_MIN_DIGITS = 7

# "@" oldida harf bo'lmasin — aks holda e-pochta ham username bo'lib qolardi.
_USERNAME = re.compile(r"(?<![\w.])@[A-Za-z][A-Za-z0-9_]{3,}")

_TELEGRAM = re.compile(
    r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/\S*", re.IGNORECASE
)
_TELEGRAM_SCHEME = re.compile(r"\btg://", re.IGNORECASE)

_EMAIL = re.compile(r"[\w.+-]+@((?:[a-z0-9-]+\.)+[a-z]{2,})", re.IGNORECASE)

# Sxemali havola (http/https/www) — host'i aniq.
_URL = re.compile(r"(?:https?://|www\.)([^\s/?#<>\"']+)[^\s<>\"']*", re.IGNORECASE)
# Sxemasiz domen: "uni-assist.de", "daad.de/stipendien". Birinchi qism
# kamida 2 belgi — "M.Sc", "B.Sc" kabi daraja nomlari havola emas.
_BARE_DOMAIN = re.compile(
    r"(?<![\w@./-])((?:[a-z0-9][a-z0-9-]+\.)(?:[a-z0-9-]+\.)*[a-z]{2,})(?=$|[\s/,;:!?)\]]|\.(?:\s|$))",
    re.IGNORECASE,
)

_BARE_DOMAIN_WITH_PATH = re.compile(_BARE_DOMAIN.pattern + r"[^\s<>\"']*", re.IGNORECASE)


def _host_allowed(host: str, allowed: list[str]) -> bool:
    host = host.lower().strip(".").split(":", 1)[0]
    host = host.removeprefix("www.")
    for entry in allowed:
        entry = entry.lower().strip()
        if not entry:
            continue
        if entry.startswith("."):
            # Zona: ".de" -> har qanday *.de
            if host.endswith(entry):
                return True
        elif host == entry or host.endswith("." + entry):
            return True
    return False


def _has_phone(text: str) -> bool:
    for match in _DIGIT_RUN.finditer(text):
        chunk = match.group(0)
        digits = sum(ch.isdigit() for ch in chunk)
        if chunk.startswith("+") and digits >= _PLUS_PHONE_MIN_DIGITS:
            return True
        if digits >= _PHONE_MIN_DIGITS:
            return True
    return False


def find_violation(text: str, allowed_domains: list[str]) -> Violation | None:
    """Birinchi topilgan buzilish yoki None (matn toza)."""
    if _TELEGRAM.search(text) or _TELEGRAM_SCHEME.search(text):
        return Violation.TELEGRAM_LINK

    # E-pochtani havolalardan OLDIN tekshiramiz va matndan olib tashlaymiz:
    # aks holda uning domeni "sxemasiz havola" bo'lib ikkinchi marta sanalardi.
    for match in _EMAIL.finditer(text):
        if not _host_allowed(match.group(1), allowed_domains):
            return Violation.EMAIL
    rest = _EMAIL.sub(" ", text)

    if _USERNAME.search(rest):
        return Violation.USERNAME

    for match in _URL.finditer(rest):
        if not _host_allowed(match.group(1), allowed_domains):
            return Violation.LINK
    without_urls = _URL.sub(" ", rest)
    for match in _BARE_DOMAIN.finditer(without_urls):
        if not _host_allowed(match.group(1), allowed_domains):
            return Violation.LINK
    without_urls = _BARE_DOMAIN_WITH_PATH.sub(" ", without_urls)

    # Ruxsat etilgan havola yo'lidagi raqamlar ("/2024/123456789") telefon emas.
    if _has_phone(without_urls):
        return Violation.PHONE
    return None
