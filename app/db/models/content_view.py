from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContentView(Base):
    """Dastur yoki grant sahifasini ko'rish.

    Bir odam bir sahifani bir kunda (Toshkent kuni) bir marta ko'rgan
    hisoblanadi: sahifaga qayta-qayta kirish sonni sun'iy oshirmasin.
    Ko'rishlar soni — shu jadvaldagi qatorlar soni.
    """

    __tablename__ = "content_views"

    # "program" yoki "grant" (app/services/view_service.py).
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    target_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
