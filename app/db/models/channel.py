from sqlalchemy import BigInteger, Boolean, String
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


class SubscriptionExemption(TimestampMixin, Base):
    """Majburiy obunadan ozod qilingan foydalanuvchi.

    Telegram ID bo'yicha ishlaydi, `users` jadvaliga bog'lanmagan: odam
    hali botga kirmagan bo'lsa ham uni oldindan ozod qilib qo'yish mumkin
    (masalan hamkor yoki jamoa a'zosi birinchi marta kirishidan oldin).

    Ro'yxatga tushgan odam uchun kanal umuman tekshirilmaydi — Telegram'ga
    so'rov ham ketmaydi.
    """

    __tablename__ = "subscription_exemptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    # Kim va nega ozod qilingani — oylar o'tib "bu kim edi" degan savol
    # tug'ilmasligi uchun.
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __str__(self) -> str:
        return self.note or str(self.telegram_id)
