"""Deep link parser: grammatika jadvalidagi barcha misollar va chekka holatlar."""

import pytest

from app.services.deeplink import (
    build_param,
    normalize_target,
    parse_start_param,
    resolve_target,
    validate_param,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "ads_de_law_a",
            {"source": "ads", "campaign": "de_law", "variant": "a", "referrer_id": None},
        ),
        ("ch_post_1105", {"source": "channel", "campaign": "post_1105", "variant": None}),
        ("tt_video_12", {"source": "tiktok", "campaign": "video_12", "variant": None}),
        ("ig_reel_3_b", {"source": "instagram", "campaign": "reel_3", "variant": "b"}),
        ("yt_shorts", {"source": "youtube", "campaign": "shorts", "variant": None}),
        ("pt_ielts_samarqand", {"source": "partner", "campaign": "ielts_samarqand"}),
        ("ref_84512", {"source": "referral", "referrer_id": 84512, "campaign": None}),
        # Eski taklif havolalari (pastki chiziqsiz) ham ishlashda davom etadi.
        ("ref84512", {"source": "referral", "referrer_id": 84512}),
        ("p_123", {"source": "share", "target": {"screen": "program", "id": 123}}),
        ("g_45", {"source": "share", "target": {"screen": "grant", "id": 45}}),
        (
            "p_123_r_84512",
            {"source": "share", "target": {"screen": "program", "id": 123}, "referrer_id": 84512},
        ),
        ("xyz", {"source": "unknown", "target": {"screen": "home"}}),
    ],
)
def test_grammar_table(raw, expected):
    parsed = parse_start_param(raw).as_dict()
    for key, value in expected.items():
        assert parsed[key] == value, (raw, key, parsed)


def test_unknown_prefix_keeps_raw_value():
    parsed = parse_start_param("xyz")
    assert parsed.source == "unknown"
    assert parsed.raw == "xyz"


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_empty_is_organic(raw):
    parsed = parse_start_param(raw)
    assert parsed.source == "organic"
    assert parsed.target == {"screen": "home"}


def test_65_chars_is_invalid_and_goes_home():
    parsed = parse_start_param("a" * 65)
    assert parsed.source == "invalid"
    assert parsed.target == {"screen": "home"}
    assert parse_start_param("a" * 64).source == "unknown"


@pytest.mark.parametrize("raw", ["ads de", "ads_de.law", "ref_1;drop", "p_1/2", "кириллица"])
def test_disallowed_chars_are_invalid(raw):
    parsed = parse_start_param(raw)
    assert parsed.source == "invalid"
    assert parsed.target == {"screen": "home"}


def test_parser_never_raises_on_odd_input():
    for raw in (123, b"bytes", object(), ["x"], "ads_", "ads__", "_", "-", "p_", "g_x"):
        parse_start_param(raw)  # exception bo'lmasligi kerak


def test_campaign_key_groups_variants():
    a = parse_start_param("ads_de_law_a")
    b = parse_start_param("ads_de_law_b")
    assert a.campaign_key == b.campaign_key == "ads_de_law"


def test_two_letter_last_segment_is_part_of_campaign():
    # `de_uk` — kampaniya, "uk" variant emas (variant faqat bitta belgi).
    parsed = parse_start_param("ads_de_uk")
    assert parsed.campaign == "de_uk"
    assert parsed.variant is None


def test_topup_is_internal_and_not_attributed():
    parsed = parse_start_param("topup")
    assert parsed.source == "internal"
    assert not parsed.counts_for_attribution


def test_build_and_validate_param():
    assert build_param("ads", "DE_Law", "A") == "ads_de_law_a"
    assert validate_param("ads_de_law_a") is None
    assert validate_param("x" * 65) is not None
    assert validate_param("ads de") is not None


def test_normalize_target_drops_garbage():
    assert normalize_target({"screen": "programs", "country": "de", "field": "law"}) == {
        "screen": "programs",
        "country": "DE",
        "field": "law",
    }
    assert normalize_target({"screen": "hack"}) == {"screen": "home"}
    assert normalize_target({"screen": "program", "id": "x"}) == {"screen": "home"}
    assert normalize_target(None) == {"screen": "home"}


async def test_missing_program_resolves_to_home(session):
    assert await resolve_target(session, parse_start_param("p_999999")) == {"screen": "home"}
    assert await resolve_target(session, parse_start_param("g_999999")) == {"screen": "home"}


async def test_campaign_mapping_resolves_and_falls_back(session):
    from app.db.models import CampaignLink

    session.add(
        CampaignLink(
            prefix="ads",
            campaign="de_law",
            variant="a",
            param="ads_de_law_a",
            target={"screen": "programs", "country": "DE", "field": "law"},
        )
    )
    await session.commit()

    # Variant b uchun alohida havola yaratilmagan — mapping baribir ishlaydi.
    assert await resolve_target(session, parse_start_param("ads_de_law_b")) == {
        "screen": "programs",
        "country": "DE",
        "field": "law",
    }
    assert await resolve_target(session, parse_start_param("ads_other")) == {"screen": "home"}
    assert await resolve_target(session, parse_start_param("ref_1")) == {"screen": "home"}
