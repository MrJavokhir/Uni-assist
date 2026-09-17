from datetime import datetime
from zoneinfo import ZoneInfo

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


def to_tashkent(dt_utc: datetime) -> datetime:
    """Baza UTC'da saqlangan vaqtni foydalanuvchiga ko'rsatish uchun Toshkent vaqtiga o'giradi."""
    return dt_utc.astimezone(TASHKENT_TZ)


def format_tashkent(dt_utc: datetime) -> str:
    return to_tashkent(dt_utc).strftime("%Y-%m-%d %H:%M")
