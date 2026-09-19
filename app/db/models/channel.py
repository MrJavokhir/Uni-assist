from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RequiredChannel(TimestampMixin, Base):
    """Botdan foydalanish uchun majburiy obuna bo'lish kerak bo'lgan kanal.

    `chat_id` — Telegram API'ga uzatiladigan identifikator: ochiq kanal uchun
    "@kanalnomi", yopiq kanal uchun "-100..." ko'rinishidagi raqam. Admin faqat
    havolani kiritsa, ochiq kanallar uchun u havoladan avtomatik chiqariladi
    (app/services/subscription_service.py).

    MUHIM: tekshiruv ishlashi uchun bot kanalda administrator bo'lishi shart.
    """

    __tablename__ = "required_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_url: Mapped[str] = mapped_column(String(500), nullable=False)
    chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __str__(self) -> str:
        return self.title
