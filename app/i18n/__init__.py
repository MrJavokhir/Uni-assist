import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"
SUPPORTED_LANGUAGES = ("uz", "ru", "en")
DEFAULT_LANGUAGE = "uz"


@lru_cache
def _load(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def t(key: str, lang: str | None = None, **kwargs: object) -> str:
    """Tarjima matnini qaytaradi. Kalit topilmasa uz'dan, undan ham topilmasa kalitning o'zidan qaytadi."""
    lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    catalog = _load(lang)
    template = catalog.get(key)
    if template is None and lang != DEFAULT_LANGUAGE:
        template = _load(DEFAULT_LANGUAGE).get(key)
    if template is None:
        template = key
    return template.format(**kwargs) if kwargs else template
