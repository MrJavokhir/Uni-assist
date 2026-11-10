"""Sovg'a qutisi (Kit xizmatiga chegirma) va admin paneldan xabar yuborish."""

import random
from decimal import Decimal

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import (
    AdmissionService,
    BalanceTransaction,
    Broadcast,
    Gift,
    ServiceFile,
    ServiceKind,
    ServiceRequest,
    UiLanguage,
    User,
    UserGift,
)
from app.services import broadcast_service as bs
from app.services import gift_service
from app.webapp import api
from app.webapp.schemas import ServiceInquiryIn


async def _guide(session, code="cv", price=Decimal(20000)) -> AdmissionService:
    service = AdmissionService(
        code=code, title_uz=f"Qo'llanma {code}", kind=ServiceKind.FILE, price_amount=price
    )
    session.add(service)
    await session.flush()
    session.add(
        ServiceFile(
            service_id=service.id,
            filename=f"{code}.pdf",
            content_type="application/pdf",
            size_bytes=3,
            data=b"pdf",
        )
    )
    await session.flush()
    return service


async def _reload(session, user_tg: int):
    """`request_service` xizmatni `session.get` bilan oladi — fayl bog'lanishi
    yuklanishi uchun sessiya tozalanadi (tests/test_service_unlock.py)."""
    await session.commit()
    session.expunge_all()
    return (await session.execute(select(User).where(User.telegram_id == user_tg))).scalar_one()


async def test_box_shows_only_with_active_gift_and_opens_once(session) -> None:
    user = User(telegram_id=1)
    session.add(user)
    await session.flush()
    assert await gift_service.gift_available(session, user) is False

    cv = await _guide(session, "cv")
    sop = await _guide(session, "sop")
    hidden = await _guide(session, "old")
    hidden.is_active = False
    session.add_all(
        [
            Gift(service_id=cv.id, discount_percent=100, weight=1),
            Gift(service_id=sop.id, discount_percent=50, weight=3),
            # Xizmati o'chiq va sovg'aning o'zi o'chiq — tushmaydi.
            Gift(service_id=hidden.id, discount_percent=100, weight=100),
            Gift(service_id=cv.id, discount_percent=100, weight=100, is_active=False),
        ]
    )
    await session.commit()
    assert await gift_service.gift_available(session, user) is True

    opened = await gift_service.open_gift(session, user, rng=random.Random(1))
    assert opened.service_id in (cv.id, sop.id)
    again = await gift_service.open_gift(session, user, rng=random.Random(2))
    assert again.id == opened.id, "quti bir marta ochiladi"
    assert await gift_service.gift_available(session, user) is False


async def test_weights_drive_the_draw(session) -> None:
    cv = await _guide(session, "cv")
    sop = await _guide(session, "sop")
    session.add_all(
        [
            Gift(service_id=cv.id, discount_percent=100, weight=1),
            Gift(service_id=sop.id, discount_percent=50, weight=9),
        ]
    )
    users = [User(telegram_id=100 + i) for i in range(200)]
    session.add_all(users)
    await session.commit()
    rng = random.Random(7)
    for user in users:
        await gift_service.open_gift(session, user, rng=rng)
    sop_count = len(
        (await session.execute(select(UserGift).where(UserGift.service_id == sop.id))).all()
    )
    assert 160 <= sop_count <= 195


def test_discount_math() -> None:
    assert gift_service.discounted(Decimal(20000), 100) == 0
    assert gift_service.discounted(Decimal(20000), 25) == 15000
    assert gift_service.discounted(Decimal(9999), 50) == 5000


async def test_free_gift_unlocks_guide_without_charging(session) -> None:
    cv = await _guide(session, "cv")
    other = await _guide(session, "sop")
    user = User(telegram_id=5, balance=Decimal(0))
    session.add(user)
    await session.flush()
    session.add(UserGift(user_id=user.id, service_id=cv.id, discount_percent=100))
    user = await _reload(session, 5)

    services = {s.code: s for s in await api.list_services(user, session)}
    assert services["cv"].gift_discount == 100
    assert services["sop"].gift_discount is None

    result = await api.request_service(cv.id, payload=None, user=user, session=session)
    assert result.requested is True
    assert result.gift_discount == 100
    assert result.charged == 0
    request = (await session.execute(select(ServiceRequest))).scalar_one()
    assert request.gift_discount == 100
    assert (await session.execute(select(BalanceTransaction))).first() is None
    gift = (await session.execute(select(UserGift))).scalar_one()
    assert gift.used_at is not None

    # Sovg'a boshqa xizmatga o'tmaydi: pul yetmasa 402.
    user = await _reload(session, 5)
    with pytest.raises(api.HTTPException) as err:
        await api.request_service(other.id, payload=None, user=user, session=session)
    assert err.value.status_code == 402


async def test_partial_gift_charges_discounted_price(session) -> None:
    cv = await _guide(session, "cv", price=Decimal(20000))
    user = User(telegram_id=6, balance=Decimal(20000))
    session.add(user)
    await session.flush()
    session.add(UserGift(user_id=user.id, service_id=cv.id, discount_percent=25))
    user = await _reload(session, 6)

    result = await api.request_service(cv.id, payload=None, user=user, session=session)

    assert result.charged == 15000
    assert result.balance == 5000


async def test_gift_is_shown_to_admins_on_request_service(session, monkeypatch) -> None:
    messages = []

    async def fake_notify(_session, html):
        messages.append(html)
        return True

    monkeypatch.setattr(api, "_notify_admins", fake_notify)
    service = AdmissionService(code="full", title_uz="To'liq yordam", kind=ServiceKind.REQUEST)
    user = User(telegram_id=7, username="aziz")
    session.add_all([service, user])
    await session.flush()
    session.add(UserGift(user_id=user.id, service_id=service.id, discount_percent=100))
    await session.commit()

    await api.send_service_inquiry(
        service.id, ServiceInquiryIn(topics=["documents"], contact="@aziz"), user, session
    )

    assert "🎁 Sovg'a: <b>bepul</b>" in messages[0]
    gift = (await session.execute(select(UserGift))).scalar_one()
    assert gift.used_at is not None


async def test_open_gift_endpoint(session) -> None:
    cv = await _guide(session, "cv", price=Decimal(20000))
    session.add(Gift(service_id=cv.id, discount_percent=25))
    user = User(telegram_id=8, ui_language=UiLanguage.UZ)
    session.add(user)
    await session.commit()

    out = await api.open_gift(user, session)

    assert (out.service_code, out.kind, out.discount_percent) == ("cv", "file", 25)
    assert (out.price_amount, out.new_price) == (20000, 15000)
    assert await gift_service.gift_available(session, user) is False


# ---- Xabar yuborish ----


class _Bot:
    def __init__(self) -> None:
        self.sent: list[int] = []

    async def send_message(self, chat_id, text, reply_markup=None):
        if chat_id == 3:
            raise TelegramForbiddenError(
                method=SendMessage(chat_id=chat_id, text=text), message="Forbidden"
            )
        self.sent.append(chat_id)

    class session:
        @staticmethod
        async def close() -> None:
            pass


def test_validation() -> None:
    assert bs.validate("", False, "", "webapp", "") == "Xabar matni bo'sh."
    assert "uzun" in bs.validate("x" * 1100, True, "", "webapp", "")
    assert bs.validate("x" * 1100, False, "", "webapp", "") is None
    assert "https" in bs.validate("Salom", False, "Ochish", "url", "ftp://x")
    assert bs.validate("Salom", False, "Ochish", "url", "https://uniassist.uz") is None


async def test_broadcast_reaches_audience_and_counts(session, monkeypatch) -> None:
    session.add_all(
        [
            User(telegram_id=1, ui_language=UiLanguage.UZ),
            User(telegram_id=2, ui_language=UiLanguage.RU),
            User(telegram_id=3, ui_language=UiLanguage.UZ),  # botni bloklagan
            User(telegram_id=4, ui_language=UiLanguage.UZ, is_blocked=True),
        ]
    )
    broadcast = Broadcast(text="<b>Salom</b>", audience="uz", status=bs.STATUS_SENDING)
    session.add(broadcast)
    await session.commit()
    assert await bs.count_recipients(session, "uz") == 2
    assert await bs.count_recipients(session, "all") == 3

    bot = _Bot()
    monkeypatch.setattr(bs, "new_bot", lambda: bot)
    monkeypatch.setattr(bs, "_SEND_INTERVAL", 0)
    monkeypatch.setattr(
        bs, "async_session_factory", async_sessionmaker(session.bind, expire_on_commit=False)
    )

    await bs.run_broadcast(broadcast.id)

    assert bot.sent == [1]
    await session.refresh(broadcast)
    assert (broadcast.status, broadcast.total, broadcast.sent, broadcast.blocked) == (
        bs.STATUS_DONE,
        2,
        1,
        1,
    )
    user3 = (await session.execute(select(User).where(User.telegram_id == 3))).scalar_one()
    assert user3.is_blocked is False, "403 hisobni bloklamaydi"


def test_html_problems_are_caught_before_sending() -> None:
    assert bs.html_problem('Salom <b>do\'st</b> &amp; <a href="https://x.uz">havola</a>') is None
    assert "&" in bs.html_problem("Narx: 10 & 20")
    assert "<" in bs.html_problem("x < 5")
    assert "yopilmagan" in bs.html_problem("<b>ochiq qoldi")
    assert "ishlamaydi" in bs.html_problem("<div>blok</div>")
    assert "href" in bs.html_problem("<a>havola</a>")
    assert bs.validate("<b>ochiq", False, "", "webapp", "") is not None


class _BrokenBot:
    def __init__(self) -> None:
        self.calls = 0

    async def send_message(self, chat_id, text, reply_markup=None):
        self.calls += 1
        raise TelegramBadRequest(
            method=SendMessage(chat_id=chat_id, text=text),
            message="Bad Request: can't parse entities",
        )

    class session:
        @staticmethod
        async def close() -> None:
            pass


async def test_broadcast_stops_when_every_message_fails(session, monkeypatch) -> None:
    session.add_all([User(telegram_id=1000 + i) for i in range(15)])
    broadcast = Broadcast(text="Salom", audience="all", status=bs.STATUS_SENDING)
    session.add(broadcast)
    await session.commit()
    bot = _BrokenBot()
    monkeypatch.setattr(bs, "new_bot", lambda: bot)
    monkeypatch.setattr(bs, "_SEND_INTERVAL", 0)
    monkeypatch.setattr(
        bs, "async_session_factory", async_sessionmaker(session.bind, expire_on_commit=False)
    )

    await bs.run_broadcast(broadcast.id)

    assert bot.calls == bs.ABORT_AFTER_FAILURES, "15 kishiga emas, 10 tadan keyin to'xtaydi"
    await session.refresh(broadcast)
    assert broadcast.status == bs.STATUS_FAILED
    assert (broadcast.sent, broadcast.failed, broadcast.total) == (0, 10, 15)
    assert "can't parse entities" in broadcast.last_error
