"""Haftalik "sizga mos dastur" xabari va Mini App qo'ng'iroqchasi."""

from datetime import UTC, date, datetime, timedelta

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendPhoto
from sqlalchemy import select

from app.db.models import (
    Country,
    DegreeLevel,
    Field,
    HomeUpdate,
    MatchNotification,
    NotificationLog,
    NotificationType,
    Program,
    SavedProgram,
    UiLanguage,
    University,
    UpdateKind,
    User,
)
from app.services import match_notification_service as mns
from app.webapp import api

TODAY = date(2026, 11, 10)  # seshanba
T0 = datetime(2026, 11, 1, 6, tzinfo=UTC)


class _Bot:
    def __init__(self, photo_error: Exception | None = None) -> None:
        self.photos: list[tuple] = []
        self.messages: list[tuple] = []
        self.photo_error = photo_error

    async def send_photo(self, chat_id, photo, **kwargs) -> None:
        if self.photo_error is not None:
            raise self.photo_error
        self.photos.append((chat_id, photo, kwargs))

    async def send_message(self, chat_id, text, **kwargs) -> None:
        self.messages.append((chat_id, text, kwargs))


@pytest.fixture(autouse=True)
def _webapp(monkeypatch):
    monkeypatch.setattr(mns.share_card.settings, "webapp_url", "https://uniassist.uz/webapp/")


async def _catalog(session):
    country = Country(iso_code="DE", name_uz="Germaniya", name_ru="Германия", name_en="Germany")
    field = Field(code="law", name_uz="Huquq", name_ru="Право", name_en="Law", sort_order=0)
    session.add_all([country, field])
    await session.flush()
    university = University(country_id=country.id, name="TUM", city="Munich", timezone="UTC")
    session.add(university)
    await session.flush()
    return country, field, university


def _program(university, field, name, created_at, degree=DegreeLevel.MASTER) -> Program:
    return Program(
        university_id=university.id,
        name=name,
        degree_level=degree,
        field_id=field.id,
        language_of_instruction="English",
        duration_years=1,
        intake_term="2027 Fall",
        source_url="https://example.com",
        verified_at=T0,
        verified_by="tester",
        created_at=created_at,
    )


async def _user(session, country, field, tg=1001, **extra) -> User:
    user = User(
        telegram_id=tg,
        ui_language=UiLanguage.UZ,
        degree_level=DegreeLevel.MASTER,
        field_id=field.id,
        **extra,
    )
    user.target_countries = [country]
    session.add(user)
    await session.flush()
    return user


async def test_weekly_match_sends_newest_unsent_program_once(session) -> None:
    country, field, uni = await _catalog(session)
    old = _program(uni, field, "Old LLM", T0)
    new = _program(uni, field, "New LLM", T0 + timedelta(days=3))
    saved = _program(uni, field, "Saved LLM", T0 + timedelta(days=5))
    other_degree = _program(
        uni, field, "Bachelor law", T0 + timedelta(days=6), DegreeLevel.BACHELOR
    )
    session.add_all([old, new, saved, other_degree])
    await session.flush()
    user = await _user(session, country, field)
    session.add(SavedProgram(user_id=user.id, program_id=saved.id))
    # Bildirishnomani o'chirgan va filtri to'liq bo'lmagan userlarga ketmaydi.
    await _user(session, country, field, tg=1002, notifications_enabled=False)
    session.add(User(telegram_id=1003, ui_language=UiLanguage.UZ))
    await session.commit()

    bot = _Bot()
    first = await mns.run_match_scan(bot, session, today=TODAY)
    assert (first.eligible_users, first.sent) == (1, 1)
    chat_id, photo, kwargs = bot.photos[0]
    assert chat_id == 1001
    assert photo.startswith(f"https://uniassist.uz/api/webapp/share/program/{new.id}.jpg?lang=uz")
    assert kwargs["caption"].startswith("✨ Siz tanlagan davlat va yo'nalish bo'yicha")
    assert "<b>New LLM</b>" in kwargs["caption"]
    button = kwargs["reply_markup"].inline_keyboard[0][0]
    assert button.text == "📖 Dastur bilan tanishish"
    assert button.web_app.url == f"https://uniassist.uz/webapp/#program_{new.id}"

    later = datetime.now(UTC) + timedelta(days=7)
    second = await mns.run_match_scan(bot, session, today=TODAY + timedelta(days=7), now=later)
    assert second.sent == 1
    assert f"/share/program/{old.id}.jpg" in bot.photos[1][1]

    # Saqlangani va boshqa darajadagisi tavsiya qilinmaydi — mos dastur qolmadi.
    third = await mns.run_match_scan(
        bot, session, today=TODAY + timedelta(days=14), now=later + timedelta(days=7)
    )
    assert (third.sent, third.no_match) == (0, 1)
    sent_ids = (
        (await session.execute(select(MatchNotification.program_id).order_by(MatchNotification.id)))
        .scalars()
        .all()
    )
    assert sent_ids == [new.id, old.id]


async def test_photo_failure_falls_back_to_text(session) -> None:
    country, field, uni = await _catalog(session)
    session.add(_program(uni, field, "LLM", T0))
    await _user(session, country, field)
    await session.commit()
    error = TelegramBadRequest(
        method=SendPhoto(chat_id=1, photo="x"),
        message="Bad Request: failed to get HTTP URL content",
    )
    bot = _Bot(photo_error=error)

    result = await mns.run_match_scan(bot, session, today=TODAY)

    assert result.sent == 1
    assert bot.messages and bot.messages[0][1].startswith("✨")


async def test_blocked_bot_marks_user(session) -> None:
    country, field, uni = await _catalog(session)
    session.add(_program(uni, field, "LLM", T0))
    user = await _user(session, country, field)
    await session.commit()
    error = TelegramForbiddenError(
        method=SendPhoto(chat_id=1, photo="x"), message="Forbidden: bot was blocked by the user"
    )

    result = await mns.run_match_scan(_Bot(photo_error=error), session, today=TODAY)

    assert (result.sent, result.blocked) == (0, 1)
    await session.refresh(user)
    assert user.is_blocked is True
    assert (await session.execute(select(MatchNotification))).first() is None


def test_match_day_is_tuesday() -> None:
    assert mns.is_match_day(TODAY)
    assert not mns.is_match_day(TODAY + timedelta(days=1))


async def test_inbox_merges_sources_and_tracks_unread(session) -> None:
    country, field, uni = await _catalog(session)
    program = _program(uni, field, "LLM", T0)
    session.add(program)
    await session.flush()
    user = await _user(session, country, field, inbox_seen_at=T0 + timedelta(days=2))
    session.add_all(
        [
            # Ko'rilgandan oldin — o'qilgan.
            HomeUpdate(
                title="Eski yangilik",
                title_en="Old news",
                kind=UpdateKind.INFO,
                published_on=date(2026, 11, 1),
                created_at=T0,
            ),
            HomeUpdate(
                title="Yashirin",
                kind=UpdateKind.INFO,
                published_on=date(2026, 11, 4),
                is_active=False,
                created_at=T0 + timedelta(days=3),
            ),
            # Ko'rilgandan keyin — o'qilmagan.
            NotificationLog(
                user_id=user.id,
                program_id=program.id,
                notif_type=NotificationType.EXACT_14D,
                sent_at=T0 + timedelta(days=3),
            ),
            MatchNotification(
                user_id=user.id, program_id=program.id, sent_at=T0 + timedelta(days=4)
            ),
        ]
    )
    await session.commit()

    inbox = await api.get_inbox(user, session)

    assert [(i.kind, i.title, i.unread) for i in inbox.items] == [
        ("match", "LLM", True),
        ("reminder", "LLM", True),
        ("info", "Eski yangilik", False),
    ]
    assert inbox.unread == 2
    assert inbox.items[0].program_id == program.id
    assert inbox.items[0].subtitle == "TUM"
    assert inbox.items[2].title_en == "Old news"

    await api.mark_inbox_seen(user, session)
    assert (await api.get_inbox(user, session)).unread == 0


async def test_recently_notified_user_is_skipped(session) -> None:
    """Qo'lda yuborilgandan keyin seshanba kuni ikkinchi xabar ketmaydi."""
    country, field, uni = await _catalog(session)
    session.add_all([_program(uni, field, "A", T0), _program(uni, field, "B", T0)])
    await _user(session, country, field)
    await session.commit()
    bot = _Bot()

    first = await mns.run_match_scan(bot, session, today=TODAY)
    again = await mns.run_match_scan(bot, session, today=TODAY + timedelta(days=4))

    assert first.sent == 1
    assert (again.sent, again.recent) == (0, 1)
    assert len(bot.photos) == 1


def test_next_match_day() -> None:
    assert mns.next_match_day(TODAY) == TODAY  # seshanba
    assert mns.next_match_day(TODAY + timedelta(days=1)) == TODAY + timedelta(days=7)
