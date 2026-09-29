"""Adminka kirishi va sessiya muddati.

Sessiya HARAKATSIZLIK bo'yicha tugaydi: har bir adminka so'rovi vaqtni
yangilaydi, oxirgi so'rovdan `admin_session_timeout_minutes` daqiqa
o'tgach esa qayta kirish talab qilinadi. Ochiq qoldirilgan adminka
cheksiz ochiq turmasligi kerak.

Vaqt SESSIYADA saqlanadi (imzolangan cookie), shuning uchun serverda
saqlanadigan holat kerak emas va bir nechta worker bo'lsa ham bir xil
ishlaydi.

Cookie'ning o'z muddati ATAYLAB uzunroq (bir kun). Uni ham 20 daqiqa
qilib qo'yilganda Starlette cookie'ni serverga yetib kelishidan oldin
bekor qilardi va adminka "nega chiqarib yubordi" degan savolga javob
bera olmasdi — foydalanuvchi sababsiz login sahifasida topilardi.
Xavfsizlik jihatidan yo'qotish yo'q: sessiya haqiqiyligini baribir
server tekshiradi, eskirgan cookie esa o'tmaydi. Bir kunlik muddat
faqat tashlab ketilgan cookie brauzerda abadiy qolmasligi uchun.
"""

import time

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import settings

SESSION_KEY = "admin_authenticated"
# Kirgan admin login'i — import/sehrgar yozgan yozuvlarda `verified_by`
# sifatida saqlanadi (kim tekshirgani ko'rinib tursin).
USERNAME_KEY = "admin_username"
# Oxirgi harakat vaqti (unix soniya).
LAST_SEEN_KEY = "admin_last_seen"

# Login sahifasiga shu belgi bilan qaytariladi — adminka nega chiqarib
# yuborganini aytishi kerak, aks holda "parolim ishlamayapti" degan
# taassurot qoladi (xabarni admin.js ko'rsatadi).
EXPIRED_FLAG = "expired"


# Cookie brauzerda abadiy qolmasligi uchun. Sessiyaning haqiqiy muddati
# emas — uni server tekshiradi (modul boshidagi izoh).
COOKIE_MAX_AGE_SECONDS = 24 * 60 * 60


def _timeout_seconds() -> int:
    return max(settings.admin_session_timeout_minutes, 1) * 60


class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str) -> None:
        super().__init__(secret_key=secret_key, max_age=COOKIE_MAX_AGE_SECONDS)

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == settings.admin_username and password == settings.admin_password:
            request.session[SESSION_KEY] = True
            request.session[USERNAME_KEY] = username
            request.session[LAST_SEEN_KEY] = int(time.time())
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> RedirectResponse | bool:
        """Har bir adminka so'rovida chaqiriladi.

        Statik fayllar bu yerdan o'tmaydi (ular alohida mount qilingan),
        shuning uchun rasm yoki CSS yuklanishi sessiyani "tirik" qilib
        turmaydi — faqat haqiqiy harakat hisoblanadi.
        """
        if not request.session.get(SESSION_KEY):
            return False

        last_seen = request.session.get(LAST_SEEN_KEY)
        now = int(time.time())
        # `last_seen` yo'q — bu o'zgarishdan OLDIN ochilgan sessiya.
        # Muddati noma'lum, shuning uchun qayta kirish so'raladi.
        if not isinstance(last_seen, int) or now - last_seen > _timeout_seconds():
            request.session.clear()
            return RedirectResponse(
                request.url_for("admin:login").include_query_params(**{EXPIRED_FLAG: "1"}),
                status_code=302,
            )

        request.session[LAST_SEEN_KEY] = now
        return True


def current_admin(request: Request) -> str:
    """Kirgan admin login'i. Eski sessiyada (bu o'zgarishdan oldin kirilgan)
    login saqlanmagan — u holda sozlamadagi yagona admin nomi olinadi."""
    return request.session.get(USERNAME_KEY) or settings.admin_username
