"""Dastur va grantni ulashish: karta rasmi, qisqa matn va bot tayyorlagan xabar."""

import io
from datetime import UTC, date, datetime

import pytest
from fastapi import HTTPException
from PIL import Image

from app.db.models import (
    Country,
    CoverageType,
    Deadline,
    DeadlineType,
    DegreeLevel,
    Program,
    ProgramCost,
    ProgramRequirement,
    Scholarship,
    ScholarshipDeadline,
    UiLanguage,
    University,
    UniversityChoiceType,
    User,
)
from app.services import share_card
from app.webapp import api

TODAY = date(2026, 11, 5)


async def _program(session) -> Program:
    country = Country(iso_code="DE", name_uz="Germaniya", name_ru="Германия", name_en="Germany")
    session.add(country)
    await session.flush()
    university = University(
        country_id=country.id, name="University of Freiburg", city="Freiburg", timezone="UTC"
    )
    session.add(university)
    await session.flush()
    program = Program(
        university_id=university.id,
        name="Sustainable Systems Engineering & <Energy>",
        degree_level=DegreeLevel.MASTER,
        language_of_instruction="English",
        duration_years=2,
        intake_term="2027 Fall",
        notes="Uzun izoh matni. " * 30,
        requirements_text=(
            "Bakalavr diplomi (240 ECTS)\n- Motivatsiya xati\n\n" + "Juda uzun talab " * 20
        ),
        has_scholarship=True,
        source_url="https://example.com",
        verified_at=datetime(2026, 1, 1, tzinfo=UTC),
        verified_by="tester",
    )
    session.add(program)
    await session.flush()
    session.add_all(
        [
            ProgramCost(
                program_id=program.id, tuition_amount=3000, currency="EUR", last_checked=TODAY
            ),
            ProgramRequirement(program_id=program.id, ielts_min=6.5, toefl_min=90),
            # O'tib ketgan muddat e'tiborga olinmaydi, eng yaqin keyingisi olinadi.
            Deadline(
                program_id=program.id,
                type=DeadlineType.APPLICATION_CLOSE,
                date_utc=datetime(2026, 3, 15, tzinfo=UTC),
                intake_term="2026 Fall",
            ),
            Deadline(
                program_id=program.id,
                type=DeadlineType.APPLICATION_CLOSE,
                date_utc=datetime(2027, 5, 15, tzinfo=UTC),
                intake_term="2027 Fall",
            ),
        ]
    )
    await session.commit()
    return await api._load_share_program(session, program.id)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    async def no_image(url):
        return None

    monkeypatch.setattr(share_card, "fetch_image", no_image)
    share_card._card_cache.clear()


def test_short_dates_per_language() -> None:
    day = date(2027, 5, 15)
    assert share_card.format_short_date(day, "uz") == "15-may"
    assert share_card.format_short_date(day, "ru") == "15 мая"
    assert share_card.format_short_date(day, "en") == "May 15"
    assert share_card.format_short_date(day, "xx") == "15-may"


async def test_caption_is_short_escaped_and_localized(session) -> None:
    program = await _program(session)
    caption = share_card.build_caption(program, "uz", TODAY)
    assert caption.startswith("<b>Sustainable Systems Engineering &amp; &lt;Energy&gt;</b>")
    assert "University of Freiburg · Freiburg, Germaniya" in caption
    assert "Magistratura · 2 yil · Ingliz tili" in caption
    assert "Muddat: 15-may" in caption
    assert "Kontrakt (yiliga): 3 000 EUR" in caption
    assert "o'z stipendiyasi" in caption
    # Faqat asosiy faktlar: uzun izoh ham, talablar ham yozilmaydi.
    assert "Uzun izoh" not in caption
    assert "Talablar" not in caption
    assert "Bakalavr diplomi" not in caption
    assert caption.endswith("🏅 Dasturning o'z stipendiyasi bor")

    english = share_card.build_caption(program, "en", TODAY)
    assert "Closes May 15" in english
    assert "Master's · 2 yr · English" in english


async def test_card_renders_jpeg_without_any_images(session) -> None:
    program = await _program(session)
    data = share_card.card_data(program, "en", TODAY)
    assert data.deadline == "Closes May 15"
    assert data.country == "Germany"
    image = Image.open(io.BytesIO(share_card.render_card(data)))
    assert image.format == "JPEG"
    assert image.size == (share_card.CARD_W, share_card.CARD_H)


def test_broken_images_do_not_break_the_card() -> None:
    data = share_card.CardData(
        title="A" * 300, subtitle="B" * 200, country="Germany", iso_code="de", deadline=None
    )
    jpeg = share_card.render_card(data, cover=b"not an image", logo=b"x", flag=b"y")
    assert Image.open(io.BytesIO(jpeg)).size == (share_card.CARD_W, share_card.CARD_H)


async def test_public_image_endpoint(session) -> None:
    program = await _program(session)
    response = await api.share_program_image(program.id, "ru", session)
    assert response.media_type == "image/jpeg"
    assert Image.open(io.BytesIO(response.body)).format == "JPEG"
    with pytest.raises(HTTPException) as err:
        await api.share_program_image(999999, "uz", session)
    assert err.value.status_code == 404


async def test_prepare_share_builds_photo_with_button(session, monkeypatch) -> None:
    program = await _program(session)
    user = User(telegram_id=84512, ui_language=UiLanguage.UZ)
    session.add(user)
    await session.commit()

    saved = {}

    class _Prepared:
        id = "prep-1"

    class _Bot:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def save_prepared_inline_message(self, **kwargs):
            saved.update(kwargs)
            return _Prepared()

        class session:
            @staticmethod
            async def close() -> None:
                pass

    async def username():
        return "assistuni_bot"

    monkeypatch.setattr(api, "Bot", _Bot)
    monkeypatch.setattr(api, "_get_bot_username", username)
    monkeypatch.setattr(api.settings, "bot_token", "123:test")
    monkeypatch.setattr(api.settings, "miniapp_short_name", "app")
    monkeypatch.setattr(api.settings, "webapp_url", "https://uniassist.uz/webapp/")

    out = await api.prepare_program_share(program.id, user, session)
    assert out.id == "prep-1"
    assert saved["user_id"] == 84512
    result = saved["result"]
    assert result.photo_url.startswith(
        f"https://uniassist.uz/api/webapp/share/program/{program.id}.jpg?lang=uz&v="
    )
    button = result.reply_markup.inline_keyboard[0][0]
    assert button.text == "📖 Dastur bilan tanishish"
    assert button.url == f"https://t.me/assistuni_bot/app?startapp=p_{program.id}_r_84512"
    assert "Germaniya" in result.caption


async def test_prepare_share_fails_softly_without_bot(session, monkeypatch) -> None:
    program = await _program(session)
    user = User(telegram_id=84513)
    session.add(user)
    await session.commit()
    monkeypatch.setattr(api.settings, "bot_token", "")
    with pytest.raises(HTTPException) as err:
        await api.prepare_program_share(program.id, user, session)
    assert err.value.status_code == 503


async def _grant(session) -> Scholarship:
    countries = [
        Country(iso_code="KR", name_uz="Janubiy Koreya", name_ru="Корея", name_en="South Korea"),
        Country(iso_code="JP", name_uz="Yaponiya", name_ru="Япония", name_en="Japan"),
    ]
    session.add_all(countries)
    await session.flush()
    grant = Scholarship(
        name="GKS",
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        degree_levels=["master", "phd"],
        stipend_amount=900000,
        stipend_period="month",
        currency="KRW",
        extras_flight=True,
        extras_insurance=True,
        ielts_min=5.5,
        age_limit=40,
        requirements_text="GPA 80%+",
        requirements_text_en="GPA 80% or higher",
        source_url="https://example.com",
        verified_at=datetime(2026, 1, 1, tzinfo=UTC),
        verified_by="tester",
    )
    grant.countries = countries
    session.add(grant)
    await session.flush()
    session.add(
        ScholarshipDeadline(
            scholarship_id=grant.id,
            type=DeadlineType.APPLICATION_CLOSE,
            date_utc=datetime(2027, 3, 1, 12, tzinfo=UTC),
            intake_term="2027",
        )
    )
    await session.commit()
    return await api._load_share_grant(session, grant.id)


async def test_grant_caption_and_card(session) -> None:
    grant = await _grant(session)
    caption = share_card.build_grant_caption(grant, "uz", TODAY)
    assert caption.startswith("<b>GKS</b>\n🌍 Janubiy Koreya, Yaponiya")
    assert "🎓 Magistratura, PhD · To'liq qoplaydi" in caption
    assert "📅 Muddat: 1-mart" in caption
    assert "💰 Stipendiya: 900 000 KRW oyiga" in caption
    assert "🎁 Aviachipta · Sug'urta" in caption
    assert caption.endswith("🎁 Aviachipta · Sug'urta")  # talablar yozilmaydi
    assert "Full coverage" in share_card.build_grant_caption(grant, "en", TODAY)

    data = share_card.grant_card_data(grant, "uz", TODAY)
    assert data.country == "2 ta davlat"
    assert data.iso_code == ""  # bir nechta davlat — bayroqsiz
    assert data.subtitle == "To'liq qoplaydi · 900 000 KRW oyiga"
    response = await api.share_grant_image(grant.id, "uz", session)
    assert Image.open(io.BytesIO(response.body)).format == "JPEG"


async def test_prepare_grant_share(session, monkeypatch) -> None:
    grant = await _grant(session)
    user = User(telegram_id=84514, ui_language=UiLanguage.EN)
    session.add(user)
    await session.commit()
    saved = {}

    class _Prepared:
        id = "prep-g"

    class _Bot:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def save_prepared_inline_message(self, **kwargs):
            saved.update(kwargs)
            return _Prepared()

        class session:
            @staticmethod
            async def close() -> None:
                pass

    async def username():
        return "assistuni_bot"

    monkeypatch.setattr(api, "Bot", _Bot)
    monkeypatch.setattr(api, "_get_bot_username", username)
    monkeypatch.setattr(api.settings, "bot_token", "123:test")
    monkeypatch.setattr(api.settings, "miniapp_short_name", "")
    monkeypatch.setattr(api.settings, "webapp_url", "https://uniassist.uz/webapp/")

    out = await api.prepare_grant_share(grant.id, user, session)
    assert out.id == "prep-g"
    result = saved["result"]
    assert f"/api/webapp/share/grant/{grant.id}.jpg?lang=en&v=" in result.photo_url
    button = result.reply_markup.inline_keyboard[0][0]
    assert button.text == "📖 View the grant"
    assert button.url == f"https://t.me/assistuni_bot?start=g_{grant.id}_r_84514"
