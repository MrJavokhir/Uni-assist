"""Admission Kit — pullik xizmatlar katalogi, PDF qo'llanmalar va so'rovlar.

Katalog KODDA emas, bazada: xizmat qo'shish, matnini tahrirlash, narxini
o'zgartirish va vaqtincha o'chirish — hammasi admin panel orqali. Shuning
uchun narx yoki ro'yxat o'zgarganda deploy kerak emas.

Xizmatning ikki turi bor va ular ALOHIDA maydon bilan belgilanmaydi —
PDF biriktirilgan-biriktirilmagani hal qiladi:

    PDF biriktirilgan  -> raqamli mahsulot. Balansdan pul yechiladi va fayl
                          shu zahoti botda yuboriladi. Sotib olinmaguncha
                          ilovada QULFLANGAN turadi.
    PDF yo'q           -> qo'lda bajariladigan xizmat (mentor, yordam).
                          Pul yechiladi, keyin admin bog'lanadi.

Shu qaror ataylab: adminga "bu qanday xizmat" degan qo'shimcha tanlov
bermaydi — fayl yuklandi, demak yuklab olinadigan mahsulot.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, str_enum

if TYPE_CHECKING:
    from app.db.models.user import User


class ServiceRequestStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    DONE = "done"
    CANCELLED = "cancelled"


class AdmissionService(TimestampMixin, Base):
    """Admission Kit sahifasidagi bitta xizmat yoki qo'llanma."""

    __tablename__ = "admission_services"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Barqaror kalit: Mini App shu kod bo'yicha ikonka tanlaydi, shuning
    # uchun nomni tahrirlash ko'rinishni buzmaydi.
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    title_uz: Mapped[str] = mapped_column(String(150), nullable=False)
    title_ru: Mapped[str | None] = mapped_column(String(150), nullable=True)
    title_en: Mapped[str | None] = mapped_column(String(150), nullable=True)

    description_uz: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Narx ko'rsatilmasa (NULL) Mini App "Narx kelishiladi" deb yozadi —
    # 0 yozib qo'yish "bepul" degan noto'g'ri ma'no berardi.
    price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="UZS")
    # "bir marta", "1 soat", "oyiga" kabi qisqa izoh — narx yonida chiqadi.
    price_note_uz: Mapped[str | None] = mapped_column(String(60), nullable=True)
    price_note_ru: Mapped[str | None] = mapped_column(String(60), nullable=True)
    price_note_en: Mapped[str | None] = mapped_column(String(60), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # `lazy="selectin"` — ilova va adminkada xizmat o'qilganda faylning
    # METAMA'LUMOTI (nomi, o'lchami) birga keladi, shuning uchun "PDF bormi"
    # degan savolga qo'shimcha so'rovsiz javob beriladi. Faylning O'ZI
    # (`ServiceFile.data`) deferred — u bu yerga TORTILMAYDI.
    file: Mapped["ServiceFile | None"] = relationship(
        back_populates="service",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __str__(self) -> str:
        return self.title_uz


class ServiceRequest(TimestampMixin, Base):
    """Foydalanuvchining xizmatga qiziqishi.

    To'lov emas, ariza: admin ro'yxatni ko'rib, foydalanuvchi bilan o'zi
    bog'lanadi va holatni yangilab boradi.
    """

    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("admission_services.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[ServiceRequestStatus] = mapped_column(
        str_enum(ServiceRequestStatus, "service_request_status"),
        nullable=False,
        default=ServiceRequestStatus.NEW,
    )
    # Admin uchun ishchi izoh (kim bilan gaplashildi, nima kelishildi).
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    service: Mapped["AdmissionService"] = relationship()
    user: Mapped["User"] = relationship()

    def __str__(self) -> str:
        return f"So'rov #{self.id}"
