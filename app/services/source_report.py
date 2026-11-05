"""Admin paneldagi "Manbalar" hisoboti: qaysi manba FAOL foydalanuvchi olib keladi.

Kohort — foydalanuvchining `first_seen_at` sanasi (Toshkent vaqti) tanlangan
oraliqqa tushganlar. Har bir qatorda (manba, kampaniya yoki variant) o'sha
kohortdagi odamlarning qanchasi keyingi qadamlarga yetgani hisoblanadi.
Hodisalar vaqtga cheklanmaydi: oraliqda kelgan odam bugun filtrni to'ldirsa
ham hisobga kiradi.

* D1 — `first_seen` kunidan keyingi kalendar kunida faol bo'lgan;
* D7 — 7–13-kunlar oralig'ida faol bo'lgan;
* faollik — `start` yoki `app_opened` hodisasi.

D1/D7 faqat "yetilgan" odamlar orasida hisoblanadi (D1 uchun keyingi kun
tugagan bo'lishi, D7 uchun kamida 14 kun o'tgan bo'lishi kerak). Guruhda
yetilgan odam bo'lmasa qiymat yo'q ("—").

Xarajat qatorga uning kaliti bo'yicha tushadi (`ads`, `ads_de_law`,
`ads_de_law_a`) va yuqori darajaga yig'iladi. Xarajat davri sana oralig'iga
qisman tushsa, kunlarga mutanosib bo'linadi.

`legacy` (bu tizimdan oldingi) foydalanuvchilar hisobotga kirmaydi — ular
uchun hodisalar yo'q va foizlarni buzib ko'rsatardi.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CampaignCost, Event, User
from app.services import event_service as ev
from app.services.deeplink import MARKETING_SOURCES, parse_start_param
from app.services.event_service import tashkent_day_bounds
from app.services.timezone_utils import TASHKENT_TZ

GROUP_SOURCE = "source"
GROUP_CAMPAIGN = "campaign"
GROUP_VARIANT = "variant"
GROUPS = (GROUP_SOURCE, GROUP_CAMPAIGN, GROUP_VARIANT)

LEGACY = "legacy"
D1_MATURE_DAYS = 2  # D1 kuni (keyingi kun) to'liq tugagan bo'lishi kerak
D7_MATURE_DAYS = 14

_FLAG_EVENTS = (ev.GATE_PASSED, ev.APP_OPENED, ev.FILTER_COMPLETED, ev.FIRST_SAVE)


@dataclass
class _Cohort:
    user_id: int
    source: str
    raw: str | None
    first_day: date


@dataclass
class ReportRow:
    key: str
    source: str
    users: int = 0
    gate: int = 0
    app: int = 0
    filter: int = 0
    save: int = 0
    d1_active: int = 0
    d1_mature: int = 0
    d7_active: int = 0
    d7_mature: int = 0
    cost: Decimal | None = None

    @staticmethod
    def _pct(part: int, whole: int) -> float | None:
        return round(part * 100 / whole, 1) if whole else None

    @property
    def gate_pct(self) -> float | None:
        return self._pct(self.gate, self.users)

    @property
    def app_pct(self) -> float | None:
        return self._pct(self.app, self.users)

    @property
    def filter_pct(self) -> float | None:
        return self._pct(self.filter, self.users)

    @property
    def save_pct(self) -> float | None:
        return self._pct(self.save, self.users)

    @property
    def d1_pct(self) -> float | None:
        return self._pct(self.d1_active, self.d1_mature)

    @property
    def d7_pct(self) -> float | None:
        return self._pct(self.d7_active, self.d7_mature)

    @property
    def cost_per_active(self) -> Decimal | None:
        """1 faol user narxi = xarajat / filtrni to'ldirganlar soni."""
        if self.cost is None or not self.filter:
            return None
        return (self.cost / self.filter).quantize(Decimal("0.01"))


@dataclass
class FunnelStep:
    key: str
    label: str
    count: int
    step_pct: float | None  # oldingi qadamdan o'tganlar foizi


@dataclass
class Report:
    date_from: date
    date_to: date
    group: str
    rows: list[ReportRow] = field(default_factory=list)
    funnel: list[FunnelStep] = field(default_factory=list)
    total: ReportRow | None = None


def _source_of_cost_key(key: str) -> str:
    key = key.strip().lower()
    return MARKETING_SOURCES.get(key, key)


def group_key(source: str, raw: str | None, group: str) -> str:
    """Foydalanuvchi qaysi qatorga tushadi."""
    if group == GROUP_SOURCE or not raw:
        return source
    parsed = parse_start_param(raw)
    if parsed.campaign_key is None:
        return source
    if group == GROUP_VARIANT and parsed.variant:
        return f"{parsed.campaign_key}_{parsed.variant}"
    return parsed.campaign_key


def cost_key(raw_key: str, group: str) -> tuple[str, str]:
    """Xarajat kaliti -> (qator kaliti shu darajada, manba).

    `ads` -> butun manba; `ads_de_law` -> kampaniya; `ads_de_law_a` -> variant.
    Pastroq darajadagi xarajat yuqori darajaga yig'iladi; yuqoriroq
    darajadagisi esa bo'linmaydi — manba nomi bilan alohida qatorda turadi.
    """
    key = raw_key.strip().lower()
    if key in MARKETING_SOURCES or key in MARKETING_SOURCES.values():
        source = _source_of_cost_key(key)
        return source, source
    parsed = parse_start_param(key)
    source = parsed.source
    if parsed.campaign_key is None:
        return key, source
    if group == GROUP_SOURCE:
        return source, source
    if group == GROUP_VARIANT and parsed.variant:
        return f"{parsed.campaign_key}_{parsed.variant}", source
    return parsed.campaign_key, source


def prorated_usd(cost: CampaignCost, date_from: date, date_to: date) -> Decimal:
    start = max(cost.period_start, date_from)
    end = min(cost.period_end, date_to)
    if end < start:
        return Decimal(0)
    period_days = (cost.period_end - cost.period_start).days + 1
    overlap_days = (end - start).days + 1
    usd = Decimal(str(cost.spend)) * Decimal(str(cost.rate_to_usd or 0))
    return usd * overlap_days / max(period_days, 1)


async def build_report(
    session: AsyncSession,
    date_from: date,
    date_to: date,
    group: str = GROUP_SOURCE,
    today: date | None = None,
) -> Report:
    group = group if group in GROUPS else GROUP_SOURCE
    today = today or datetime.now(UTC).astimezone(TASHKENT_TZ).date()
    range_start, _ = tashkent_day_bounds(date_from)
    _, range_end = tashkent_day_bounds(date_to)

    users = [
        _Cohort(
            user_id=row.id,
            source=row.first_source or "unknown",
            raw=row.first_param_raw,
            first_day=row.first_seen_at.astimezone(TASHKENT_TZ).date(),
        )
        for row in (
            await session.execute(
                select(User.id, User.first_source, User.first_param_raw, User.first_seen_at).where(
                    User.first_seen_at >= range_start,
                    User.first_seen_at < range_end,
                    User.first_source.is_not(None),
                    User.first_source != LEGACY,
                )
            )
        ).all()
    ]
    ids = [u.user_id for u in users]

    flags: dict[int, set[str]] = defaultdict(set)
    active_days: dict[int, set[date]] = defaultdict(set)
    if ids:
        for user_id, name in (
            await session.execute(
                select(Event.user_id, Event.name)
                .where(Event.user_id.in_(ids), Event.name.in_(_FLAG_EVENTS))
                .group_by(Event.user_id, Event.name)
            )
        ).all():
            flags[user_id].add(name)

        # Toshkent kuni Python'da hisoblanadi: bazada IANA tz ma'lumotlari
        # bo'lmasligi mumkin (masalan, Windows'dagi lokal Postgres).
        for user_id, created_at in (
            await session.execute(
                select(Event.user_id, Event.created_at).where(
                    Event.user_id.in_(ids), Event.name.in_(ev.ACTIVITY_EVENTS)
                )
            )
        ).all():
            active_days[user_id].add(created_at.astimezone(TASHKENT_TZ).date())

    rows: dict[str, ReportRow] = {}
    total = ReportRow(key="Jami", source="")

    def row_for(key: str, source: str) -> ReportRow:
        if key not in rows:
            rows[key] = ReportRow(key=key, source=source)
        return rows[key]

    for user in users:
        row = row_for(group_key(user.source, user.raw, group), user.source)
        user_flags = flags.get(user.user_id, set())
        days = active_days.get(user.user_id, set())
        age = (today - user.first_day).days
        for target in (row, total):
            target.users += 1
            target.gate += ev.GATE_PASSED in user_flags
            target.app += ev.APP_OPENED in user_flags
            target.filter += ev.FILTER_COMPLETED in user_flags
            target.save += ev.FIRST_SAVE in user_flags
            if age >= D1_MATURE_DAYS:
                target.d1_mature += 1
                target.d1_active += (user.first_day + timedelta(days=1)) in days
            if age >= D7_MATURE_DAYS:
                target.d7_mature += 1
                target.d7_active += any(
                    (user.first_day + timedelta(days=n)) in days for n in range(7, 14)
                )

    costs = (
        (
            await session.execute(
                select(CampaignCost).where(
                    CampaignCost.period_start <= date_to, CampaignCost.period_end >= date_from
                )
            )
        )
        .scalars()
        .all()
    )
    for cost in costs:
        usd = prorated_usd(cost, date_from, date_to)
        key, source = cost_key(cost.source_or_campaign, group)
        row = row_for(key, source)
        row.cost = (row.cost or Decimal(0)) + usd
        total.cost = (total.cost or Decimal(0)) + usd
    for row in [*rows.values(), total]:
        if row.cost is not None:
            row.cost = row.cost.quantize(Decimal("0.01"))

    funnel_counts = [
        ("start", "Kirdi (start)", total.users),
        ("app", "Mini App ochdi", total.app),
        ("gate", "Kanaldan o'tdi", total.gate),
        ("filter", "Filtr to'ldirdi", total.filter),
        ("save", "Saqladi", total.save),
    ]
    funnel = []
    previous = None
    for key, label, count in funnel_counts:
        step = ReportRow._pct(count, previous) if previous is not None else None
        funnel.append(FunnelStep(key=key, label=label, count=count, step_pct=step))
        previous = count

    ordered = sorted(rows.values(), key=lambda r: (-r.users, r.key))
    return Report(
        date_from=date_from, date_to=date_to, group=group, rows=ordered, funnel=funnel, total=total
    )


CSV_HEADER = [
    "Manba",
    "Yangi userlar",
    "Kanaldan o'tdi %",
    "Mini app ochdi %",
    "Filtr to'ldirdi %",
    "Saqladi %",
    "D1 %",
    "D7 %",
    "Xarajat (USD)",
    "1 faol user narxi (USD)",
]


def csv_rows(report: Report) -> list[list[str]]:
    def fmt(value) -> str:
        return "" if value is None else str(value)

    out = [CSV_HEADER]
    for row in [*report.rows, report.total]:
        out.append(
            [
                row.key,
                str(row.users),
                fmt(row.gate_pct),
                fmt(row.app_pct),
                fmt(row.filter_pct),
                fmt(row.save_pct),
                fmt(row.d1_pct),
                fmt(row.d7_pct),
                fmt(row.cost),
                fmt(row.cost_per_active),
            ]
        )
    return out


async def filter_completed_today(session: AsyncSession, now: datetime | None = None) -> int:
    """Bugun (Toshkent kuni) filtrni birinchi marta to'ldirganlar."""
    now = now or datetime.now(UTC)
    start, end = tashkent_day_bounds(now.astimezone(TASHKENT_TZ).date())
    stmt = select(func.count(Event.id)).where(
        Event.name == ev.FILTER_COMPLETED, Event.created_at >= start, Event.created_at < end
    )
    return (await session.execute(stmt)).scalar_one()
