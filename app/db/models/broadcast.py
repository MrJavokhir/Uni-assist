"""Admin paneldan bot orqali userlarga yuboriladigan xabar."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

BROADCAST_AUDIENCES = ("all", "uz", "ru", "en")
BUTTON_KINDS = ("webapp", "url")


class Broadcast(TimestampMixin, Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Telegram HTML: <b>, <i>, <u>, <a href>, <code>.
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    image_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    button_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # "webapp" — Mini App'ni ochadi; "url" — oddiy havola.
    button_kind: Mapped[str | None] = mapped_column(String(10), nullable=True)
    button_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # "all" yoki interfeys tili: "uz" / "ru" / "en".
    audience: Mapped[str] = mapped_column(String(10), nullable=False, default="all")
    # sending -> done | interrupted
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sending")
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
