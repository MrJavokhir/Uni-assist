"""'Manbalar' hisoboti: foizlar, D1/D7 (yetilganlik bilan), xarajat va narx."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.db.models import CampaignCost, Event, User
from app.services import source_report
from app.services.source_report import GROUP_CAMPAIGN, GROUP_VARIANT, build_report, csv_rows

TODAY = date(2026, 11, 5)
# Toshkent vaqti bilan 11:00 — kun chegarasidan uzoq.
COHORT_AT = datetime(2026, 10, 16, 6, tzinfo=UTC)  # 20 kun oldin
FRESH_AT = datetime(2026, 11, 5, 6, tzinfo=UTC)  # bugun


async def _user(session, tg: int, source: str, raw: str | None, seen: datetime) -> User:
    user = User(telegram_id=tg, first_source=source, first_param_raw=raw, first_seen_at=seen)
    session.add(user)
    await session.flush()
    return user


def _event(user: User, name: str, at: datetime) -> Event:
    return Event(user_id=user.id, name=name, created_at=at)


async def _seed(session):
    a1 = await _user(session, 1, "ads", "ads_de_law_a", COHORT_AT)
    a2 = await _user(session, 2, "ads", "ads_de_law_a", COHORT_AT)
    b1 = await _user(session, 3, "ads", "ads_de_law_b", COHORT_AT)
    b2 = await _user(session, 4, "ads", "ads_de_law_b", COHORT_AT)
    tt = await _user(session, 5, "tiktok", "tt_video_12", FRESH_AT)
    # Bu tizimdan oldingi foydalanuvchi hisobotga kirmaydi.
    await _user(session, 6, "legacy", None, COHORT_AT)

    day = timedelta(days=1)
    session.add_all(
        [
            *[_event(u, "start", COHORT_AT) for u in (a1, a2, b1, b2)],
            *[_event(u, "app_opened", COHORT_AT) for u in (a1, a2, b1, b2)],
            *[_event(u, "gate_passed", COHORT_AT) for u in (a1, a2, b1)],
            *[_event(u, "filter_completed", COHORT_AT) for u in (a1, b1)],
            _event(a1, "first_save", COHORT_AT),
            # D1: ertasi kuni faol — a1 va b2.
            _event(a1, "app_opened", COHORT_AT + day),
            _event(b2, "start", COHORT_AT + day),
            # D7: 8-kuni faol — faqat a2. 14-kun D7 oynasidan tashqarida.
            _event(a2, "app_opened", COHORT_AT + 8 * day),
            _event(b1, "app_opened", COHORT_AT + 14 * day),
            # D1 hisobiga kirmaydi: faollik emas.
            _event(b1, "save", COHORT_AT + day),
            _event(tt, "start", FRESH_AT),
            _event(tt, "app_opened", FRESH_AT),
        ]
    )
    session.add_all(
        [
            CampaignCost(
                source_or_campaign="ads_de_law",
                spend=100,
                currency="USD",
                rate_to_usd=1,
                period_start=date(2026, 10, 10),
                period_end=date(2026, 10, 19),
            ),
            CampaignCost(
                source_or_campaign="tt",
                spend=1_265_000,
                currency="UZS",
                rate_to_usd=Decimal("0.000079"),
                period_start=date(2026, 11, 1),
                period_end=date(2026, 11, 5),
            ),
        ]
    )
    await session.commit()


async def test_source_rows_percentages_retention_and_cost(session) -> None:
    await _seed(session)
    report = await build_report(session, date(2026, 10, 7), TODAY, today=TODAY)
    rows = {r.key: r for r in report.rows}

    assert set(rows) == {"ads", "tiktok"}
    ads = rows["ads"]
    assert ads.users == 4
    assert ads.gate_pct == 75.0
    assert ads.app_pct == 100.0
    assert ads.filter_pct == 50.0
    assert ads.save_pct == 25.0
    assert ads.d1_pct == 50.0  # a1, b2
    assert ads.d7_pct == 25.0  # a2
    assert ads.cost == Decimal("100.00")
    assert ads.cost_per_active == Decimal("50.00")  # 100 / 2 filtr to'ldirgan

    tiktok = rows["tiktok"]
    assert tiktok.users == 1
    # Bugun kelgan — hali yetilmagan.
    assert tiktok.d1_pct is None
    assert tiktok.d7_pct is None
    assert tiktok.cost == Decimal("99.94")  # 1 265 000 so'm * 0.000079
    assert tiktok.cost_per_active is None  # filtr to'ldirgan yo'q

    assert report.total.users == 5
    funnel = {step.key: (step.count, step.step_pct) for step in report.funnel}
    assert funnel == {
        "start": (5, None),
        "app": (5, 100.0),
        "gate": (3, 60.0),
        "filter": (2, 66.7),
        "save": (1, 50.0),
    }


async def test_campaign_and_variant_grouping(session) -> None:
    await _seed(session)
    by_campaign = await build_report(session, date(2026, 10, 7), TODAY, GROUP_CAMPAIGN, today=TODAY)
    rows = {r.key: r for r in by_campaign.rows}
    assert rows["ads_de_law"].users == 4
    assert rows["ads_de_law"].cost == Decimal("100.00")
    assert rows["tt_video_12"].users == 1
    # Butun manbaga yozilgan xarajat kampaniyalarga bo'linmaydi.
    assert rows["tiktok"].users == 0
    assert rows["tiktok"].cost == Decimal("99.94")

    by_variant = await build_report(session, date(2026, 10, 7), TODAY, GROUP_VARIANT, today=TODAY)
    rows = {r.key: r for r in by_variant.rows}
    assert rows["ads_de_law_a"].users == 2
    assert rows["ads_de_law_a"].filter_pct == 50.0
    assert rows["ads_de_law_b"].users == 2
    assert rows["ads_de_law_b"].d1_pct == 50.0


async def test_cost_is_prorated_and_range_limits_cohort(session) -> None:
    await _seed(session)
    # Faqat 16–19 oktyabr: 10 kunlik xarajatning 4 kuni, tiktok kohorti tashqarida.
    report = await build_report(session, date(2026, 10, 16), date(2026, 10, 19), today=TODAY)
    rows = {r.key: r for r in report.rows}
    assert set(rows) == {"ads"}
    assert rows["ads"].cost == Decimal("40.00")
    assert rows["ads"].cost_per_active == Decimal("20.00")


async def test_csv_has_header_rows_and_total(session) -> None:
    await _seed(session)
    report = await build_report(session, date(2026, 10, 7), TODAY, today=TODAY)
    table = csv_rows(report)
    assert table[0] == source_report.CSV_HEADER
    assert table[-1][0] == "Jami"
    assert len(table) == 1 + len(report.rows) + 1


async def test_filter_completed_today_counts_tashkent_day(session) -> None:
    user = await _user(session, 7, "ads", "ads_x", FRESH_AT)
    session.add_all(
        [
            # 4-noyabr 19:30 UTC = Toshkentda 5-noyabr 00:30 -> bugun.
            Event(
                user_id=user.id,
                name="filter_completed",
                created_at=datetime(2026, 11, 4, 19, 30, tzinfo=UTC),
            ),
        ]
    )
    other = await _user(session, 8, "ads", "ads_x", FRESH_AT)
    session.add(
        Event(
            user_id=other.id,
            name="filter_completed",
            created_at=datetime(2026, 11, 4, 18, 30, tzinfo=UTC),  # Toshkentda 4-noyabr 23:30
        )
    )
    await session.commit()
    now = datetime(2026, 11, 5, 10, tzinfo=UTC)
    assert await source_report.filter_completed_today(session, now) == 1
