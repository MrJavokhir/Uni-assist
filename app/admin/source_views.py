"""Admin: "Manbalar" — reklama manbalari hisoboti, havola generatori, xarajatlar.

* `/admin/sources` — kohort hisoboti (app/services/source_report.py) va CSV;
* `/admin/links` — deep link generatori: ikkala formatdagi havola va
  kampaniya -> ekran mapping'i (`campaign_links`);
* "Kampaniya xarajatlari" — oddiy SQLAdmin formasi (`CampaignCostAdmin`).
"""

import csv
import io
import logging
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqladmin import BaseView, ModelView, expose
from sqlalchemy import select, update
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from wtforms import SelectField

from app.config import settings
from app.db.models import CampaignCost, CampaignLink, Country, Field, Program, Scholarship
from app.db.models.analytics import COST_CURRENCIES
from app.db.session import async_session_factory
from app.services import source_report
from app.services.deeplink import (
    MARKETING_SOURCES,
    SCREEN_GRANT,
    SCREEN_GRANTS,
    SCREEN_HOME,
    SCREEN_PROGRAM,
    SCREEN_PROGRAMS,
    build_param,
    normalize_target,
    parse_start_param,
    validate_param,
)
from app.services.timezone_utils import TASHKENT_TZ

logger = logging.getLogger(__name__)

DEFAULT_RANGE_DAYS = 30
FALLBACK_BOT_USERNAME = "assistuni_bot"

SOURCE_LABELS = {
    "ads": "Telegram Ads",
    "ch": "Kanal posti",
    "tt": "TikTok",
    "ig": "Instagram",
    "yt": "YouTube",
    "pt": "Hamkor",
}
SCREEN_LABELS = {
    SCREEN_HOME: "Bosh sahifa",
    SCREEN_PROGRAMS: "Dasturlar ro'yxati",
    SCREEN_GRANTS: "Grantlar",
    SCREEN_PROGRAM: "Aniq dastur",
    SCREEN_GRANT: "Aniq grant",
}
GROUP_LABELS = {
    source_report.GROUP_SOURCE: "Manba",
    source_report.GROUP_CAMPAIGN: "Kampaniya",
    source_report.GROUP_VARIANT: "Variant",
}
_CAMPAIGN_RE = re.compile(r"^[a-z0-9-]+(?:_[a-z0-9-]+)*$")


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


async def _bot_username() -> str:
    from app.webapp.api import _get_bot_username

    try:
        return await _get_bot_username() or FALLBACK_BOT_USERNAME
    except Exception:
        logger.exception("Bot nomini aniqlab bo'lmadi")
        return FALLBACK_BOT_USERNAME


def build_links(bot_username: str, param: str) -> dict[str, str | None]:
    short_name = settings.miniapp_short_name.strip()
    return {
        "start": f"https://t.me/{bot_username}?start={param}",
        "startapp": f"https://t.me/{bot_username}/{short_name}?startapp={param}"
        if short_name
        else None,
    }


class SourcesView(BaseView):
    name = "Hisobot"
    category = "Manbalar"
    icon = "fa-solid fa-chart-line"

    @expose("/sources", methods=["GET"], identity="sources")
    async def page(self, request: Request):
        today = datetime.now(UTC).astimezone(TASHKENT_TZ).date()
        date_to = _parse_date(request.query_params.get("to")) or today
        date_from = _parse_date(request.query_params.get("from")) or (
            date_to - timedelta(days=DEFAULT_RANGE_DAYS - 1)
        )
        if date_from > date_to:
            date_from, date_to = date_to, date_from
        group = request.query_params.get("group") or source_report.GROUP_SOURCE

        async with async_session_factory() as session:
            report = await source_report.build_report(session, date_from, date_to, group, today)

        if request.query_params.get("format") == "csv":
            buffer = io.StringIO()
            csv.writer(buffer).writerows(source_report.csv_rows(report))
            filename = f"manbalar_{date_from}_{date_to}.csv"
            # BOM — Excel o'zbekcha harflarni to'g'ri ochishi uchun.
            return Response(
                "﻿" + buffer.getvalue(),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        return await self.templates.TemplateResponse(
            request,
            "sources.html",
            {
                "report": report,
                "group_labels": GROUP_LABELS,
                "csv_query": request.url.include_query_params(
                    format="csv",
                    **{
                        "from": date_from.isoformat(),
                        "to": date_to.isoformat(),
                        "group": report.group,
                    },
                ).query,
            },
        )


class LinksView(BaseView):
    name = "Havola generatori"
    category = "Manbalar"
    icon = "fa-solid fa-link"

    async def _context(self, request: Request, **extra) -> dict:
        async with async_session_factory() as session:
            links = (
                (await session.execute(select(CampaignLink).order_by(CampaignLink.id.desc())))
                .scalars()
                .all()
            )
            country_rows = (
                await session.execute(
                    select(Country.iso_code, Country.name_uz)
                    .where(Country.hidden.is_(False))
                    .order_by(Country.name_uz)
                )
            ).all()
            fields = (
                await session.execute(select(Field.code, Field.name_uz).order_by(Field.sort_order))
            ).all()
        bot_username = await _bot_username()
        country_names = dict(country_rows)
        field_names = dict(fields)
        return {
            "links": [
                {
                    "row": link,
                    "urls": build_links(bot_username, link.param),
                    "target": describe_target(link.target, country_names, field_names),
                }
                for link in links
            ],
            "countries": country_rows,
            "fields": fields,
            "source_labels": SOURCE_LABELS,
            "screen_labels": SCREEN_LABELS,
            "short_name": settings.miniapp_short_name.strip(),
            "bot_username": bot_username,
            **extra,
        }

    @expose("/links", methods=["GET", "POST"], identity="links")
    async def page(self, request: Request):
        if request.method == "GET":
            return await self.templates.TemplateResponse(
                request, "links.html", await self._context(request, form={})
            )

        form = dict(await request.form())
        error, param, target = await validate_link_form(form)
        if error:
            return await self.templates.TemplateResponse(
                request, "links.html", await self._context(request, form=form, error=error)
            )
        await save_link(form, param, target)
        bot_username = await _bot_username()
        return await self.templates.TemplateResponse(
            request,
            "links.html",
            await self._context(
                request, form={}, created=param, created_urls=build_links(bot_username, param)
            ),
        )

    @expose("/links/delete", methods=["POST"], identity="links-delete")
    async def delete(self, request: Request):
        form = await request.form()
        try:
            link_id = int(form.get("id") or 0)
        except ValueError:
            link_id = 0
        async with async_session_factory() as session:
            link = await session.get(CampaignLink, link_id)
            if link is not None:
                await session.delete(link)
                await session.commit()
        return RedirectResponse(request.url_for("admin:links"), status_code=303)


def describe_target(target: dict, country_names: dict, field_names: dict) -> str:
    target = normalize_target(target)
    label = SCREEN_LABELS.get(target["screen"], target["screen"])
    if target["screen"] == SCREEN_PROGRAMS:
        parts = [
            country_names.get(target.get("country"), target.get("country")),
            field_names.get(target.get("field"), target.get("field")),
        ]
        parts = [p for p in parts if p]
        if parts:
            label += ": " + " + ".join(parts)
    elif target["screen"] in (SCREEN_PROGRAM, SCREEN_GRANT):
        label += f" #{target['id']}"
    return label


async def validate_link_form(form: dict) -> tuple[str | None, str, dict]:
    """(xato, parametr, target). Xato bo'lsa birinchi element — matn."""
    prefix = (form.get("prefix") or "").strip().lower()
    campaign = (form.get("campaign") or "").strip().lower()
    variant = (form.get("variant") or "").strip().lower()
    screen = form.get("screen") or SCREEN_HOME

    if prefix not in MARKETING_SOURCES:
        return "Manba turini tanlang.", "", {}
    if not campaign or not _CAMPAIGN_RE.match(campaign):
        return (
            (
                "Kampaniya nomi: lotin harflari, raqamlar va '-', so'zlar orasida '_' "
                "(masalan: de_law)."
            ),
            "",
            {},
        )
    if variant and not re.fullmatch(r"[a-z0-9]", variant):
        return "Variant — bitta harf yoki raqam (a, b, 1...).", "", {}

    param = build_param(prefix, campaign, variant or None)
    problem = validate_param(param)
    if problem:
        return problem, param, {}
    # Parser havolani AYNAN shu kampaniya va variant deb o'qishi kerak:
    # masalan `post_1` kampaniyasi `post` + variant `1` bo'lib ketardi.
    parsed = parse_start_param(param)
    if parsed.campaign != campaign or (parsed.variant or "") != variant:
        return (
            (
                "Kampaniya nomining oxirgi qismi bitta belgidan iborat bo'lmasin — u variant "
                f"deb o'qiladi. Masalan '{campaign}' o'rniga '{campaign}x' yoki boshqa nom."
            ),
            param,
            {},
        )

    raw_target: dict = {"screen": screen}
    if screen == SCREEN_PROGRAMS:
        raw_target.update(country=form.get("country") or "", field=form.get("field") or "")
    elif screen in (SCREEN_PROGRAM, SCREEN_GRANT):
        raw_target["id"] = form.get("item_id")
    target = normalize_target(raw_target)
    if target["screen"] != screen:
        return "Dastur yoki grant ID raqamini to'g'ri kiriting.", param, {}

    if screen in (SCREEN_PROGRAM, SCREEN_GRANT):
        model = Program if screen == SCREEN_PROGRAM else Scholarship
        async with async_session_factory() as session:
            if await session.get(model, target["id"]) is None:
                kind = "Dastur" if screen == SCREEN_PROGRAM else "Grant"
                return f"{kind} #{target['id']} topilmadi.", param, {}
    return None, param, target


async def save_link(form: dict, param: str, target: dict) -> None:
    """Havolani saqlaydi va kampaniya mapping'ini yangilaydi.

    Bir kampaniyaning barcha variantlari bitta ekranni ochadi, shuning uchun
    shu kampaniyadagi mavjud havolalarning target'i ham yangisiga tenglanadi.
    """
    parsed = parse_start_param(param)
    note = (form.get("note") or "").strip()[:255] or None
    async with async_session_factory() as session:
        existing = (
            await session.execute(select(CampaignLink).where(CampaignLink.param == param))
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                CampaignLink(
                    prefix=parsed.prefix,
                    campaign=parsed.campaign,
                    variant=parsed.variant,
                    param=param,
                    target=target,
                    note=note,
                )
            )
        elif note:
            existing.note = note
        await session.execute(
            update(CampaignLink)
            .where(CampaignLink.prefix == parsed.prefix, CampaignLink.campaign == parsed.campaign)
            .values(target=target)
        )
        await session.commit()


def _money(value) -> str:
    try:
        return f"{Decimal(str(value)):,.2f}"
    except (InvalidOperation, ValueError):
        return str(value)


class CampaignCostAdmin(ModelView, model=CampaignCost):
    """Kampaniya xarajatlari: "Manbalar" hisobotidagi "Xarajat" va "1 faol user narxi"."""

    name = "Kampaniya xarajati"
    name_plural = "Kampaniya xarajatlari"
    category = "Manbalar"
    icon = "fa-solid fa-coins"

    column_list = [
        CampaignCost.id,
        CampaignCost.source_or_campaign,
        CampaignCost.spend,
        CampaignCost.currency,
        CampaignCost.rate_to_usd,
        CampaignCost.period_start,
        CampaignCost.period_end,
        CampaignCost.note,
    ]
    column_default_sort = [(CampaignCost.period_start, True)]
    column_searchable_list = [CampaignCost.source_or_campaign, CampaignCost.note]
    form_columns = [
        CampaignCost.source_or_campaign,
        CampaignCost.spend,
        CampaignCost.currency,
        CampaignCost.rate_to_usd,
        CampaignCost.period_start,
        CampaignCost.period_end,
        CampaignCost.note,
    ]
    column_labels = {
        CampaignCost.id: "ID",
        CampaignCost.source_or_campaign: "Manba yoki kampaniya",
        CampaignCost.spend: "Xarajat",
        CampaignCost.currency: "Valyuta",
        CampaignCost.rate_to_usd: "Kurs (1 birlik = ? USD)",
        CampaignCost.period_start: "Boshlanish",
        CampaignCost.period_end: "Tugash",
        CampaignCost.note: "Izoh",
    }
    column_formatters = {CampaignCost.spend: lambda m, a: _money(m.spend)}
    form_overrides = {"currency": SelectField}
    form_args = {
        "source_or_campaign": {
            "description": (
                "Butun manba: ads, ch, tt, ig, yt, pt. Kampaniya: ads_de_law. "
                "Variant: ads_de_law_a."
            )
        },
        "currency": {"choices": [(c, c) for c in COST_CURRENCIES], "default": "USD"},
        "rate_to_usd": {
            "description": (
                "1 birlik valyuta necha USD. USD uchun 1. UZS uchun masalan 0.000079 "
                "(1 USD = 12 650 so'm). Qo'lda kiritiladi."
            ),
            "default": 1,
        },
        "period_start": {"description": "Xarajat davri (Toshkent sanasi)."},
    }

    async def on_model_change(
        self, data: dict, model: CampaignCost, is_created: bool, request: Request
    ) -> None:
        key = (data.get("source_or_campaign") or "").strip().lower()
        if not key or validate_param(key):
            raise ValueError("Manba yoki kampaniya: lotin harflari, raqamlar, '_' va '-'.")
        data["source_or_campaign"] = key
        if data.get("currency") not in COST_CURRENCIES:
            raise ValueError("Valyutani tanlang: USD, UZS yoki EUR.")
        if data.get("currency") == "USD":
            data["rate_to_usd"] = 1
        rate = data.get("rate_to_usd")
        if rate is None or Decimal(str(rate)) <= 0:
            raise ValueError("Kurs musbat son bo'lishi kerak.")
        spend = data.get("spend")
        if spend is None or Decimal(str(spend)) < 0:
            raise ValueError("Xarajat manfiy bo'lmasin.")
        start, end = data.get("period_start"), data.get("period_end")
        if start and end and end < start:
            raise ValueError("Tugash sanasi boshlanishdan oldin bo'lmasin.")
