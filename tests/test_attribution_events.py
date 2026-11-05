"""Atributsiya, pending_target (kanal tekshiruvidan keyin) va hodisalar."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.bot.handlers import start
from app.db.models import (
    CampaignLink,
    Country,
    DegreeLevel,
    Event,
    Field,
    Program,
    RequiredChannel,
    University,
    User,
)
from app.services import attribution_service, event_service
from app.services.deeplink import parse_start_param
from app.webapp import api
from app.webapp.schemas import EventIn, ProfileIn

NOW = datetime(2026, 11, 5, 9, tzinfo=UTC)


# ---- soxta Telegram obyektlari ----
class _Member:
    def __init__(self, status: str) -> None:
        self.status = status


class _Bot:
    status = "left"

    async def get_chat_member(self, chat_id, user_id):
        return _Member(_Bot.status)

    async def send_message(self, *args, **kwargs) -> None:
        pass

    class session:
        @staticmethod
        async def close() -> None:
            pass


class _FromUser:
    def __init__(self, telegram_id: int) -> None:
        self.id = telegram_id
        self.username = f"u{telegram_id}"
        self.full_name = "Test"
        self.language_code = "en"


class _Message:
    def __init__(self, telegram_id: int) -> None:
        self.from_user = _FromUser(telegram_id)
        self.bot = _Bot()
        self.answers = []

    async def answer(self, text, reply_markup=None) -> None:
        self.answers.append((text, reply_markup))


class _Args:
    def __init__(self, args: str | None) -> None:
        self.args = args


@pytest.fixture(autouse=True)
def _fake_telegram(monkeypatch):
    _Bot.status = "left"
    monkeypatch.setattr(api, "redis_client", None)
    monkeypatch.setattr(api, "Bot", lambda *args, **kwargs: _Bot())
    monkeypatch.setattr(api.settings, "bot_token", "123:test")


async def _start(session, telegram_id: int, args: str | None) -> User:
    await start.cmd_start(_Message(telegram_id), session, _Args(args))
    user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one()
    await session.refresh(user)
    return user


async def _events(session, user: User, name: str) -> int:
    stmt = select(func.count(Event.id)).where(Event.user_id == user.id, Event.name == name)
    return (await session.execute(stmt)).scalar_one()


async def _profile_user(session, telegram_id: int) -> User:
    from app.services.user_service import get_or_create_user

    return await get_or_create_user(session, telegram_id, None)


# ---- atributsiya ----
async def test_first_source_is_kept_and_last_source_updates(session) -> None:
    user = await _start(session, 9001, "ads_de_law_a")
    assert user.first_source == "ads"
    assert user.first_param_raw == "ads_de_law_a"
    first_seen = user.first_seen_at
    assert first_seen is not None

    user = await _start(session, 9001, "tt_video_12")
    assert user.first_source == "ads"
    assert user.first_param_raw == "ads_de_law_a"
    assert user.first_seen_at == first_seen
    assert user.last_source == "tiktok"

    user = await _start(session, 9001, None)
    assert user.last_source == "organic"
    assert await _events(session, user, "start") == 3


async def test_topup_does_not_touch_attribution(session) -> None:
    user = await _start(session, 9002, "ch_post_1")
    # `topup` — ilova ichidagi xizmat payload'i, reklama manbai emas.
    await attribution_service.record_entry(session, user, parse_start_param("topup"), is_new=False)
    assert user.last_source == "channel"


async def test_self_invite_is_ignored(session) -> None:
    user = await _start(session, 9003, "ref_9003")
    assert user.referred_by_id is None
    assert user.first_source == "referral"


async def test_referrer_is_written_once_and_only_for_new_users(session) -> None:
    first = await _start(session, 9010, None)
    second = await _start(session, 9011, None)

    invited = await _start(session, 9012, "ref_9010")
    assert invited.referred_by_id == first.id

    # Ikkinchi taklif havolasi birinchisini almashtirmaydi.
    invited = await _start(session, 9012, "ref_9011")
    assert invited.referred_by_id == first.id

    # Eski foydalanuvchi keyinroq taklif havolasini bossa ham bog'lanmaydi.
    old = await _start(session, 9013, None)
    old = await _start(session, 9013, "ref_9011")
    assert old.referred_by_id is None
    assert second.referred_by_id is None


async def test_unknown_referrer_is_ignored(session) -> None:
    user = await _start(session, 9014, "ref_123456789")
    assert user.referred_by_id is None


async def test_share_link_attaches_referrer_and_targets_program(session) -> None:
    sharer = await _start(session, 9020, None)
    program = await _program(session)
    user = await _start(session, 9021, f"p_{program.id}_r_9020")
    assert user.referred_by_id == sharer.id
    assert user.first_source == "share"
    assert user.pending_target == {"screen": "program", "id": program.id}


# ---- kanal tekshiruvi va pending_target ----
async def _catalog(session):
    country = Country(iso_code="DE", name_uz="Germaniya", name_ru="Германия", name_en="Germany")
    field = Field(code="law", name_uz="Huquq", name_ru="Право", name_en="Law")
    session.add_all([country, field])
    await session.flush()
    session.add(
        CampaignLink(
            prefix="ads",
            campaign="de_law",
            variant="a",
            param="ads_de_law_a",
            target={"screen": "programs", "country": "DE", "field": "law"},
        )
    )
    session.add(
        RequiredChannel(
            chat_id="@uniassist_uz", title="Uni Assist", invite_url="https://t.me/uniassist_uz"
        )
    )
    await session.commit()
    return country, field


async def _program(session) -> Program:
    country = (
        await session.execute(select(Country).where(Country.iso_code == "DE"))
    ).scalar_one_or_none()
    if country is None:
        country = Country(iso_code="DE", name_uz="Germaniya", name_ru="Германия", name_en="Germany")
        session.add(country)
        await session.flush()
    university = University(country_id=country.id, name="TUM", city="Munich", timezone="UTC")
    session.add(university)
    await session.flush()
    program = Program(
        university_id=university.id,
        name="LLM",
        degree_level=DegreeLevel.MASTER,
        language_of_instruction="English",
        duration_years=1,
        intake_term="2027 Fall",
        source_url="https://example.com",
        verified_at=NOW,
        verified_by="tester",
    )
    session.add(program)
    await session.commit()
    return program


async def test_ads_link_survives_channel_gate_and_lands_on_target(session) -> None:
    country, field = await _catalog(session)
    await _start(session, 9030, "ads_de_law_a")
    user = await _profile_user(session, 9030)

    # Bot tugmasi Mini App'ni parametrsiz ochadi — maqsad bazadan keladi.
    entry = await api.app_entry(init={"start_param": None}, user=user, session=session)
    assert entry.needs_gate is True
    assert entry.target["screen"] == "programs"

    # Kanalga a'zo emas: oyna ko'rsatildi, maqsad saqlanib turibdi.
    status = await api.get_subscription(fresh=False, user=user, session=session)
    assert status.subscribed is False
    assert status.target is None
    assert await _events(session, user, "gate_shown") == 1
    assert user.pending_target is not None

    # "I joined" -> a'zo bo'ldi -> o'sha ekran, filtr bilan.
    _Bot.status = "member"
    status = await api.get_subscription(fresh=True, user=user, session=session)
    assert status.subscribed is True
    assert status.target == {
        "screen": "programs",
        "country": "DE",
        "field": "law",
        "country_id": country.id,
        "field_id": field.id,
    }
    assert user.pending_target is None
    assert await _events(session, user, "gate_passed") == 1

    # Keyingi ochilishda maqsad yo'q — oddiy bosh sahifa.
    entry = await api.app_entry(init={"start_param": None}, user=user, session=session)
    assert entry.target is None


async def test_expired_pending_target_is_not_used(session) -> None:
    await _catalog(session)
    await _start(session, 9031, "ads_de_law_a")
    user = await _profile_user(session, 9031)
    user.pending_target_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.commit()

    entry = await api.app_entry(init={"start_param": None}, user=user, session=session)
    assert entry.target is None
    _Bot.status = "member"
    status = await api.get_subscription(fresh=True, user=user, session=session)
    assert status.target is None


async def test_startapp_param_attributes_and_targets_program(session) -> None:
    program = await _program(session)
    user = await _profile_user(session, 9032)

    entry = await api.app_entry(init={"start_param": f"p_{program.id}"}, user=user, session=session)
    assert entry.target == {"screen": "program", "id": program.id}
    assert entry.needs_gate is False
    assert user.first_source == "share"
    assert user.pending_target is None  # gate kerak emas — darhol ishlatildi
    assert await _events(session, user, "app_opened") == 1

    # Kun davomida qayta ochish `app_opened`ni ko'paytirmaydi.
    await api.app_entry(init={"start_param": None}, user=user, session=session)
    assert await _events(session, user, "app_opened") == 1


async def test_plain_open_does_not_overwrite_last_source(session) -> None:
    await _start(session, 9033, "yt_shorts")
    user = await _profile_user(session, 9033)
    await api.app_entry(init={"start_param": None}, user=user, session=session)
    assert user.last_source == "youtube"


# ---- POST /events ----
async def test_events_endpoint_rejects_bad_signature(session) -> None:
    with pytest.raises(HTTPException) as err:
        await api.get_current_user(x_telegram_init_data="user=1&hash=bad", session=session)
    assert err.value.status_code == 401
    with pytest.raises(HTTPException) as err:
        await api.get_init_payload(x_telegram_init_data="user=1&hash=bad")
    assert err.value.status_code == 401


async def test_events_endpoint_whitelist(session) -> None:
    user = await _profile_user(session, 9040)
    with pytest.raises(HTTPException) as err:
        await api.post_event(EventIn(name="gate_passed"), user=user, session=session)
    assert err.value.status_code == 422
    assert await _events(session, user, "gate_passed") == 0

    result = await api.post_event(
        EventIn(name="program_viewed", props={"id": "5", "name": "Ali", "phone": "+998"}),
        user=user,
        session=session,
    )
    assert result == {"ok": True}
    row = (await session.execute(select(Event).where(Event.user_id == user.id))).scalar_one()
    assert row.props == {"id": 5}  # shaxsiy maydonlar tashlab yuborildi


async def test_events_rate_limit(session, monkeypatch) -> None:
    import fakeredis.aioredis

    monkeypatch.setattr(api, "redis_client", fakeredis.aioredis.FakeRedis())
    monkeypatch.setattr(api, "EVENTS_PER_MINUTE", 2)
    user = await _profile_user(session, 9041)
    for _ in range(2):
        await api.post_event(
            EventIn(name="grant_viewed", props={"id": 1}), user=user, session=session
        )
    with pytest.raises(HTTPException) as err:
        await api.post_event(
            EventIn(name="grant_viewed", props={"id": 1}), user=user, session=session
        )
    assert err.value.status_code == 429


# ---- bir martalik hodisalar ----
async def test_first_save_is_written_once(session) -> None:
    program = await _program(session)
    other = await _program(session)
    user = await _profile_user(session, 9050)

    await api.save_program(program.id, user=user, session=session)
    user = await _profile_user(session, 9050)
    await api.save_program(other.id, user=user, session=session)

    assert await _events(session, user, "save") == 2
    assert await _events(session, user, "first_save") == 1
    # Bazaning o'zi ham ikkinchisini qabul qilmaydi.
    assert await event_service.log(session, user, "first_save") is False
    assert await _events(session, user, "first_save") == 1


async def test_filter_completed_is_written_once(session) -> None:
    country, field = await _catalog(session)
    user = await _profile_user(session, 9051)

    await api.update_me(ProfileIn(degree_level="master"), user=user, session=session)
    assert await _events(session, user, "filter_completed") == 0

    payload = ProfileIn(field_id=field.id, target_country_ids=[country.id])
    await api.update_me(payload, user=user, session=session)
    assert await _events(session, user, "filter_completed") == 1

    await api.update_me(ProfileIn(degree_level="bachelor"), user=user, session=session)
    await api.update_me(ProfileIn(target_country_ids=[]), user=user, session=session)
    await api.update_me(ProfileIn(target_country_ids=[country.id]), user=user, session=session)
    assert await _events(session, user, "filter_completed") == 1


async def test_event_failure_never_breaks_flow(session, monkeypatch) -> None:
    user = await _profile_user(session, 9052)
    # Mavjud bo'lmagan foydalanuvchi -> FK xatosi; log jim qaytadi.
    assert await event_service.log(session, 99999999, "save") is False
    # Sessiya ishlashda davom etadi.
    assert await event_service.log(session, user, "save") is True
