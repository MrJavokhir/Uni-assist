"""Atributsiya va hodisalar: qayerdan kelgan, qayerda to'xtagan, qancha turgan.

* `events` — foydalanuvchi oqimidagi hodisalar (start, kanal, mini app,
  filtr, saqlash...). `created_at` faqat serverda qo'yiladi.
* `campaign_links` — admin paneldagi havola generatori yaratgan havolalar;
  ayni paytda kampaniya -> ochiladigan ekran mapping'i.
* `campaign_costs` — kampaniya xarajatlari (qo'lda kiritiladi).
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Bir martalik hodisalar: bazada `(user_id, name)` bo'yicha unique (qisman
# indeks), shuning uchun takroriy yozuv umuman paydo bo'lmaydi.
ONCE_EVENTS = ("gate_passed", "filter_completed", "first_save")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_user_created", "user_id", "created_at"),
        Index("ix_events_name_created", "name", "created_at"),
        Index(
            "uq_events_once",
            "user_id",
            "name",
            unique=True,
            postgresql_where=text("name IN ('gate_passed', 'filter_completed', 'first_save')"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    # Hodisa paytidagi manba (foydalanuvchining `last_source`i).
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    props: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CampaignLink(Base):
    """Generator yaratgan havola va kampaniya mapping'i.

    Mapping `(prefix, campaign)` bo'yicha o'qiladi: `ads_de_law_a` va
    `ads_de_law_b` bitta ekranni ochadi. Bir kampaniyaga bir nechta havola
    bo'lsa, eng oxirgi yaratilganining target'i amal qiladi.
    """

    __tablename__ = "campaign_links"
    __table_args__ = (Index("ix_campaign_links_prefix_campaign", "prefix", "campaign"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    campaign: Mapped[str] = mapped_column(String(64), nullable=False)
    variant: Mapped[str | None] = mapped_column(String(8), nullable=True)
    param: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    target: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __str__(self) -> str:
        return self.param


COST_CURRENCIES = ("USD", "UZS", "EUR")
# Hisobot shu valyutada: har xarajat qatori o'z kursi bilan aylantiriladi.
REPORT_CURRENCY = "USD"


class CampaignCost(Base):
    """Kampaniya xarajati. `source_or_campaign`: `ads`, `ads_de_law` yoki
    `ads_de_law_a` — hisobot jadvalining qaysi darajasiga tegishli bo'lsa."""

    __tablename__ = "campaign_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_or_campaign: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    spend: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # 1 birlik `currency` necha USD (USD uchun 1). Qo'lda kiritiladi —
    # tashqi kurs API'si ishlatilmaydi.
    rate_to_usd: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False, default=1)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __str__(self) -> str:
        return f"{self.source_or_campaign}: {self.spend} {self.currency}"
