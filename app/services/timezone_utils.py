from datetime import datetime
from zoneinfo import ZoneInfo

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


def to_tashkent(dt_utc: datetime) -> datetime:
    """Baza UTC'da saqlangan vaqtni foydalanuvchiga ko'rsatish uchun Toshkent vaqtiga o'giradi."""
    return dt_utc.astimezone(TASHKENT_TZ)


def format_tashkent(dt_utc: datetime) -> str:
    return to_tashkent(dt_utc).strftime("%Y-%m-%d %H:%M")


def from_tashkent(local_naive: datetime) -> datetime:
    """Adminka formasidan kelgan vaqtni UTC'ga o'giradi.

    `datetime-local` maydoni vaqt mintaqasini yubormaydi — faqat "2026-10-05
    14:00". Adminlar Toshkentda ishlaydi va ilova ham hamma vaqtni Toshkent
    bo'yicha ko'rsatadi, shuning uchun kiritilgan vaqt Toshkent vaqti deb
    qabul qilinadi. Aks holda serverning mintaqasiga qarab uchrashuv
    vaqtlari siljib ketardi.
    """
    return local_naive.replace(tzinfo=TASHKENT_TZ).astimezone(ZoneInfo("UTC"))


def format_deadline_date(dt_utc: datetime) -> str:
    """Deadline'ni faqat SANA sifatida ko'rsatadi ("2027-07-31").

    Katalogdagi muddatlar sana sifatida kiritiladi va UTC yarim tunda
    saqlanadi. Vaqt bilan ko'rsatilganda Toshkentga o'girilib hamma joyda
    "05:00" chiqardi — bu universitetning haqiqiy soati emas, chalg'itardi.
    """
    return to_tashkent(dt_utc).date().isoformat()
