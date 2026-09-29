"""Adminka sessiyasi harakatsizlik bo'yicha tugashi.

Ochiq qoldirilgan adminka cheksiz ochiq turmasligi kerak. Shu bilan
birga ishlab turgan odam har 20 daqiqada qayta kirishga majbur
bo'lmasligi kerak — muddat HARAKATSIZLIK bo'yicha, ya'ni har so'rovda
suriladi.
"""

import time

import pytest
from starlette.datastructures import URL
from starlette.responses import RedirectResponse

from app.admin.auth import (
    COOKIE_MAX_AGE_SECONDS,
    LAST_SEEN_KEY,
    SESSION_KEY,
    USERNAME_KEY,
    AdminAuth,
    current_admin,
)
from app.config import settings


class FakeRequest:
    """Starlette so'rovining shu testlarga kerak bo'lgan qismi."""

    def __init__(self, session: dict | None = None, form: dict | None = None) -> None:
        self.session = session if session is not None else {}
        self._form = form or {}

    async def form(self) -> dict:
        return self._form

    def url_for(self, name: str) -> URL:
        return URL(f"http://testserver/admin/{name.split(':')[-1]}")


@pytest.fixture
def backend() -> AdminAuth:
    return AdminAuth(secret_key="test-secret")


@pytest.mark.asyncio
async def test_login_stores_activity_time(backend) -> None:
    request = FakeRequest(
        form={"username": settings.admin_username, "password": settings.admin_password}
    )

    assert await backend.login(request) is True
    assert request.session[SESSION_KEY] is True
    assert request.session[USERNAME_KEY] == settings.admin_username
    assert isinstance(request.session[LAST_SEEN_KEY], int)


@pytest.mark.asyncio
async def test_wrong_password_is_refused(backend) -> None:
    request = FakeRequest(form={"username": settings.admin_username, "password": "xato"})

    assert await backend.login(request) is False
    assert request.session == {}


@pytest.mark.asyncio
async def test_anonymous_request_is_refused(backend) -> None:
    assert await backend.authenticate(FakeRequest()) is False


@pytest.mark.asyncio
async def test_active_session_passes_and_slides(backend) -> None:
    """Har so'rov muddatni uzaytiradi — ishlab turgan odam chiqarilmaydi."""
    old = int(time.time()) - 60
    request = FakeRequest({SESSION_KEY: True, LAST_SEEN_KEY: old})

    assert await backend.authenticate(request) is True
    assert request.session[LAST_SEEN_KEY] > old


@pytest.mark.asyncio
async def test_idle_session_expires(backend) -> None:
    stale = int(time.time()) - (settings.admin_session_timeout_minutes * 60 + 1)
    request = FakeRequest({SESSION_KEY: True, USERNAME_KEY: "admin", LAST_SEEN_KEY: stale})

    result = await backend.authenticate(request)

    assert isinstance(result, RedirectResponse)
    assert "expired=1" in str(result.headers["location"])
    # Sessiya tozalanadi: eski cookie bilan qaytib kirib bo'lmasligi kerak.
    assert request.session == {}


@pytest.mark.asyncio
async def test_session_on_the_edge_still_passes(backend) -> None:
    """Chegaraning ichida turgan sessiya chiqarilmaydi."""
    edge = int(time.time()) - (settings.admin_session_timeout_minutes * 60 - 5)
    request = FakeRequest({SESSION_KEY: True, LAST_SEEN_KEY: edge})

    assert await backend.authenticate(request) is True


@pytest.mark.asyncio
async def test_session_without_timestamp_expires(backend) -> None:
    """Bu o'zgarishdan OLDIN ochilgan sessiyaning muddati noma'lum.

    Uni "hali yangi" deb hisoblash cheksiz ochiq sessiyani qoldirardi,
    shuning uchun bir marta qayta kirish so'raladi.
    """
    request = FakeRequest({SESSION_KEY: True, USERNAME_KEY: "admin"})

    result = await backend.authenticate(request)

    assert isinstance(result, RedirectResponse)
    assert request.session == {}


@pytest.mark.asyncio
async def test_logout_clears_session(backend) -> None:
    request = FakeRequest({SESSION_KEY: True, LAST_SEEN_KEY: int(time.time())})

    assert await backend.logout(request) is True
    assert request.session == {}


def test_current_admin_falls_back_to_settings() -> None:
    assert current_admin(FakeRequest({USERNAME_KEY: "javohir"})) == "javohir"
    # Eski sessiyada login saqlanmagan.
    assert current_admin(FakeRequest({})) == settings.admin_username


def test_cookie_outlives_the_idle_timeout(backend) -> None:
    """Cookie muddati sessiya muddatidan UZUN bo'lishi kerak.

    Teng bo'lganda Starlette cookie'ni serverga yetib kelishidan oldin
    bekor qilardi va adminka "muddat tugadi" deb tushuntira olmasdi —
    odam sababsiz login sahifasida topilardi.
    """
    middleware = backend.middlewares[0]
    assert middleware.kwargs["max_age"] == COOKIE_MAX_AGE_SECONDS
    assert COOKIE_MAX_AGE_SECONDS > settings.admin_session_timeout_minutes * 60
