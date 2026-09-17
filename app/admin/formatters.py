from datetime import UTC, datetime

from markupsafe import Markup

VERIFIED_STALE_DAYS = 90


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
