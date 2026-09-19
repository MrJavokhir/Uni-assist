from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum

from markupsafe import Markup, escape

VERIFIED_STALE_DAYS = 90


def enum_label(labels: dict[Enum, str]) -> Callable[[object, str], str]:
    """Enum ustunini ro'yxatda o'zbekcha nomi bilan ko'rsatadi
    (SQLAdmin standart holatda `MASTER` kabi Python nomini chiqaradi)."""

    def _format(model: object, attribute: str) -> str:
        value = getattr(model, attribute)
        if value is None:
            return "—"
        return labels.get(value, getattr(value, "value", str(value)))

    return _format


def format_bool(model: object, attribute: str) -> Markup:
    value = getattr(model, attribute)
    if value is None:
        return Markup("<span class='text-muted'>—</span>")
    if value:
        return Markup("<span style='color:#16a34a;font-weight:600'>✓ Ha</span>")
    return Markup("<span class='text-muted'>✕ Yo'q</span>")


def format_university_wizard_link(model: object, attribute: str) -> Markup:
    """Universitet nomini sehrgarga havola qiladi.

    SQLAdmin'ning o'z tahrirlash formasi faqat universitetning o'z maydonlarini
    beradi — dasturlarini u yerdan qo'shib bo'lmaydi. Shuning uchun nom
    "Universitet qo'shish" sehrgariga olib boradi: u dasturlar, talablar,
    xarajatlar va muddatlar bilan birga to'ldirilgan holda ochiladi.
    """
    name = escape(getattr(model, attribute) or "—")
    return Markup(
        f"<a href='/admin/university-wizard?university_id={model.id}' "
        f"title='Dasturlari bilan birga tahrirlash'>{name}</a>"
    )


def format_program_labels(model: object, attribute: str) -> list[str]:
    """Universitet dasturlarini qisqa yorliq bilan ko'rsatadi.

    MUHIM: bu "ko'pga-ko'p"/"birga-ko'p" ustun, SQLAdmin shablonda
    `zip(value, formatted_value)` qiladi — shuning uchun bitta matn emas,
    har bir dastur uchun bittadan element qaytarish SHART. Aks holda matn
    harflab bo'linib ketadi.

    To'liq nom o'rniga qisqartma (MBA, LLM) chiqadi — ro'yxat siqiq qoladi.
    """
    programs = getattr(model, attribute) or []
    return [program.abbreviation or program.name for program in programs]


def format_verified_at(model: object, attribute: str) -> Markup:
    """verified_at 90 kundan oshgan bo'lsa ro'yxatda qizil rangda ko'rsatadi."""
    value: datetime | None = getattr(model, attribute)
    if value is None:
        return Markup("<span class='text-muted'>—</span>")

    now = datetime.now(UTC)
    days_old = (now - value).days
    text = value.strftime("%Y-%m-%d")

    if days_old > VERIFIED_STALE_DAYS:
        return Markup(
            f"<span style='color:#c0392b;font-weight:600' "
            f"title='{days_old} kun oldin tekshirilgan'>{text} ⚠</span>"
        )
    return Markup(f"<span style='color:#2f9e44'>{text}</span>")
