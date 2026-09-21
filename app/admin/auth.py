from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.config import settings

SESSION_KEY = "admin_authenticated"
# Kirgan admin login'i — import/sehrgar yozgan yozuvlarda `verified_by`
# sifatida saqlanadi (kim tekshirgani ko'rinib tursin).
USERNAME_KEY = "admin_username"


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == settings.admin_username and password == settings.admin_password:
            request.session[SESSION_KEY] = True
            request.session[USERNAME_KEY] = username
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get(SESSION_KEY))


def current_admin(request: Request) -> str:
    """Kirgan admin login'i. Eski sessiyada (bu o'zgarishdan oldin kirilgan)
    login saqlanmagan — u holda sozlamadagi yagona admin nomi olinadi."""
    return request.session.get(USERNAME_KEY) or settings.admin_username
