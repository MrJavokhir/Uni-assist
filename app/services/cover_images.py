"""Universitet va grant rasmlari (Mini App'dagi dastur/grant sahifasi tepasida).

Rasm admin panelda — universitet va grant sehrgarlarida yuklanadi va BAZADA
saqlanadi (PDF qo'llanmalar singari): Railway konteynerining fayl tizimi har
deployda tozalanadi, baza esa zaxiralanadi. Baytlar `deferred` ustunda —
ro'yxatlarda o'qilmaydi.

Mini App rasmni `/api/webapp/images/{kind}/{id}?v=N` dan oladi. `v` har yangi
yuklashda oshadi: manzil o'zgargani uchun brauzer va Telegram keshi eski
rasmni ko'rsatib qolmaydi, javob esa uzoq muddat keshlanadi.
"""

from typing import Any

MAX_COVER_BYTES = 3 * 1024 * 1024
ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}


def cover_url(kind: str, obj: Any) -> str | None:
    """Mini App uchun rasm manzili; rasm yuklanmagan bo'lsa None."""
    if not getattr(obj, "cover_version", 0):
        return None
    return f"/api/webapp/images/{kind}/{obj.id}?v={obj.cover_version}"


async def apply_cover_upload(obj: Any, upload: Any, remove: bool) -> None:
    """Sehrgar formasidagi rasmni obyektga yozadi.

    Yangi fayl tanlanmagan bo'lsa (yoki "o'chirish" belgilanmagan bo'lsa)
    mavjud rasm o'zgarmaydi. Noto'g'ri fayl `ValueError` beradi — sehrgar
    uni xato sifatida ko'rsatadi va hech narsa saqlanmaydi.
    """
    if upload is not None and getattr(upload, "filename", ""):
        content_type = (upload.content_type or "").split(";")[0].strip().lower()
        if content_type not in ALLOWED_COVER_TYPES:
            raise ValueError("Rasm JPG, PNG yoki WebP formatida bo'lishi kerak")
        data = await upload.read()
        if not data:
            raise ValueError("Rasm fayli bo'sh")
        if len(data) > MAX_COVER_BYTES:
            raise ValueError("Rasm 3 MB dan katta bo'lmasin")
        obj.cover_data = data
        obj.cover_type = content_type
        obj.cover_version = (obj.cover_version or 0) + 1
    elif remove:
        obj.cover_data = None
        obj.cover_type = None
        obj.cover_version = 0
