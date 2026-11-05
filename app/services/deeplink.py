"""Deep link parametri: qayerdan kelgani (atributsiya) va qaysi ekranga ochilishi.

Parametr ikki yo'l bilan keladi:
  * `t.me/<bot>?start=PARAM` — bot chatida `/start PARAM`;
  * `t.me/<bot>/<short_name>?startapp=PARAM` — Mini App'da imzolangan
    initData ichidagi `start_param`.

Ikkalasi ham shu yerdagi BITTA parser'dan o'tadi (`parse_start_param`), u
sof funksiya: bazaga murojaat qilmaydi va hech qachon exception
tashlamaydi — yomon parametr oqimni to'xtatmasligi kerak.

Grammatika (README, "Deep link qoidalari"):
    ads_<kampaniya>[_<variant>]   Telegram Ads
    ch_ / tt_ / ig_ / yt_ / pt_   kanal posti / TikTok / Instagram / YouTube / hamkor
    ref_<telegram_id>             do'st taklifi (eski `ref<telegram_id>` ham)
    p_<id>[_r_<telegram_id>]      dastur sahifasi (ulashgan odam bilan)
    g_<id>[_r_<telegram_id>]      grant sahifasi (ulashgan odam bilan)

Variant — oxirgi segment, faqat BITTA harf yoki raqam bo'lsa:
`ads_de_law_a` -> kampaniya `de_law`, variant `a`; `ads_de_law` -> kampaniya
`de_law`, variantsiz. Shunday qilinmasa `de_uk` kabi kampaniya nomi
"de" + variant "uk" bo'lib bo'linib ketardi.

Kampaniya qaysi ekranni ochishi kodda emas — `campaign_links` jadvalida
(admin paneldagi havola generatori yozadi). Uni `resolve_target` o'qiydi.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

PARAM_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_PARAM_LEN = 64

# Prefiks -> `users.first_source` / `last_source` dagi nom.
MARKETING_SOURCES: dict[str, str] = {
    "ads": "ads",
    "ch": "channel",
    "tt": "tiktok",
    "ig": "instagram",
    "yt": "youtube",
    "pt": "partner",
}

SOURCE_ORGANIC = "organic"
SOURCE_INVALID = "invalid"
SOURCE_UNKNOWN = "unknown"
SOURCE_REFERRAL = "referral"
SOURCE_SHARE = "share"
# Ilova ichidan keladigan xizmat payload'lari (masalan, Mini App'dagi
# "Top up" -> `?start=topup`). Bular reklama manbai emas: atributsiyaga
# yozilmaydi.
SOURCE_INTERNAL = "internal"
INTERNAL_PAYLOADS = frozenset({"topup"})

SCREEN_HOME = "home"
SCREEN_PROGRAMS = "programs"
SCREEN_GRANTS = "grants"
SCREEN_PROGRAM = "program"
SCREEN_GRANT = "grant"
SCREENS = (SCREEN_HOME, SCREEN_PROGRAMS, SCREEN_GRANTS, SCREEN_PROGRAM, SCREEN_GRANT)

_REF_RE = re.compile(r"^ref_?(\d{1,20})$")
_PAGE_RE = re.compile(r"^([pg])_(\d{1,12})(?:_r_(\d{1,20}))?$")
_VARIANT_RE = re.compile(r"^[a-z0-9]$")


def home() -> dict[str, Any]:
    return {"screen": SCREEN_HOME}


@dataclass(frozen=True)
class StartParam:
    source: str
    campaign: str | None = None
    variant: str | None = None
    target: dict[str, Any] = field(default_factory=home)
    referrer_id: int | None = None  # taklif qilgan/ulashgan odamning Telegram ID'si
    raw: str | None = None
    prefix: str | None = None  # "ads", "ch", ... (faqat marketing manbalari uchun)

    @property
    def campaign_key(self) -> str | None:
        """Hisobotda guruhlash kaliti: `ads_de_law` (variantsiz)."""
        if self.prefix and self.campaign:
            return f"{self.prefix}_{self.campaign}"
        return None

    @property
    def counts_for_attribution(self) -> bool:
        return self.source != SOURCE_INTERNAL

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "campaign": self.campaign,
            "variant": self.variant,
            "target": dict(self.target),
            "referrer_id": self.referrer_id,
        }


def _parse(raw: str) -> StartParam:
    value = raw.strip()
    if not value:
        return StartParam(source=SOURCE_ORGANIC)
    if not PARAM_RE.match(value):
        return StartParam(source=SOURCE_INVALID, raw=value[:255])
    if value.lower() in INTERNAL_PAYLOADS:
        return StartParam(source=SOURCE_INTERNAL, raw=value)

    ref = _REF_RE.match(value)
    if ref:
        return StartParam(source=SOURCE_REFERRAL, referrer_id=int(ref.group(1)), raw=value)

    page = _PAGE_RE.match(value)
    if page:
        kind, item_id, referrer = page.groups()
        screen = SCREEN_PROGRAM if kind == "p" else SCREEN_GRANT
        return StartParam(
            source=SOURCE_SHARE,
            target={"screen": screen, "id": int(item_id)},
            referrer_id=int(referrer) if referrer else None,
            raw=value,
        )

    prefix, sep, rest = value.partition("_")
    prefix = prefix.lower()
    if sep and prefix in MARKETING_SOURCES:
        segments = [s for s in rest.lower().split("_") if s]
        variant = None
        if len(segments) >= 2 and _VARIANT_RE.match(segments[-1]):
            variant = segments.pop()
        return StartParam(
            source=MARKETING_SOURCES[prefix],
            campaign="_".join(segments) or None,
            variant=variant,
            raw=value,
            prefix=prefix,
        )

    return StartParam(source=SOURCE_UNKNOWN, raw=value)


def parse_start_param(raw: object) -> StartParam:
    """Parametrni tahlil qiladi. Hech qachon exception tashlamaydi."""
    try:
        if raw is None:
            return StartParam(source=SOURCE_ORGANIC)
        return _parse(str(raw))
    except Exception:  # pragma: no cover — himoya: parser oqimni buzmasin
        logger.exception("Deep link parametrini o'qib bo'lmadi: %r", raw)
        return StartParam(source=SOURCE_INVALID)


def build_param(prefix: str, campaign: str, variant: str | None = None) -> str:
    """Generator uchun: `ads` + `de_law` + `a` -> `ads_de_law_a`."""
    parts = [prefix.strip().lower(), campaign.strip().lower()]
    if variant and variant.strip():
        parts.append(variant.strip().lower())
    return "_".join(parts)


def validate_param(param: str) -> str | None:
    """Xato matni yoki None (to'g'ri)."""
    if not param:
        return "Parametr bo'sh."
    if len(param) > MAX_PARAM_LEN:
        return f"Parametr {len(param)} belgi — ko'pi bilan {MAX_PARAM_LEN} ta bo'lishi kerak."
    if not PARAM_RE.match(param):
        return "Faqat lotin harflari, raqamlar, '_' va '-' ruxsat etilgan."
    return None


def normalize_target(raw: object) -> dict[str, Any]:
    """Bazadagi yoki formadagi target'ni xavfsiz shaklga keltiradi."""
    if not isinstance(raw, dict):
        return home()
    screen = raw.get("screen")
    if screen not in SCREENS:
        return home()
    target: dict[str, Any] = {"screen": screen}
    if screen in (SCREEN_PROGRAM, SCREEN_GRANT):
        try:
            target["id"] = int(raw.get("id"))
        except (TypeError, ValueError):
            return home()
    if screen == SCREEN_PROGRAMS:
        country = str(raw.get("country") or "").strip().upper()
        field_code = str(raw.get("field") or "").strip()
        if re.fullmatch(r"[A-Z]{2}", country):
            target["country"] = country
        if re.fullmatch(r"[A-Za-z0-9_-]{1,50}", field_code):
            target["field"] = field_code
    return target


async def resolve_target(session, parsed: StartParam) -> dict[str, Any]:
    """Parametr qaysi ekranni ochishi — bazaga qarab.

    * marketing kampaniyasi -> `campaign_links` dagi mapping (topilmasa home);
    * `p_<id>` / `g_<id>` -> dastur/grant mavjud bo'lsa o'sha sahifa, aks holda home;
    * qolgani -> home.
    Xato bo'lsa ham home — oqim to'xtamaydi.
    """
    from sqlalchemy import select

    from app.db.models import CampaignLink, Program, Scholarship

    try:
        screen = parsed.target.get("screen")
        if screen == SCREEN_PROGRAM:
            exists = await session.get(Program, parsed.target["id"])
            return dict(parsed.target) if exists is not None else home()
        if screen == SCREEN_GRANT:
            exists = await session.get(Scholarship, parsed.target["id"])
            return dict(parsed.target) if exists is not None else home()
        if parsed.prefix and parsed.campaign:
            stmt = (
                select(CampaignLink.target)
                .where(
                    CampaignLink.prefix == parsed.prefix,
                    CampaignLink.campaign == parsed.campaign,
                )
                .order_by(CampaignLink.id.desc())
                .limit(1)
            )
            mapped = (await session.execute(stmt)).scalar_one_or_none()
            if mapped:
                target = normalize_target(mapped)
                if target["screen"] in (SCREEN_PROGRAM, SCREEN_GRANT):
                    return await resolve_target(session, StartParam(source="", target=target))
                return target
    except Exception:
        logger.exception("Deep link maqsadini aniqlab bo'lmadi: %r", parsed.raw)
    return home()
