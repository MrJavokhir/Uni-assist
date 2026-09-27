"""Admission Kit — pullik xizmatlar katalogi, PDF qo'llanmalar va so'rovlar.

Katalog KODDA emas, bazada: xizmat qo'shish, matnini tahrirlash, narxini
o'zgartirish va vaqtincha o'chirish — hammasi admin panel orqali. Shuning
uchun narx yoki ro'yxat o'zgarganda deploy kerak emas.

Xizmatning turi ANIQ maydonda — `AdmissionService.kind`:

    FILE     -> yuklab olinadigan qo'llanma. Ilovada doim QULFLANGAN
                turadi, sotib olinganda pul balansdan yechiladi va PDF
                botda yuboriladi. Adminga so'rov ketmaydi: yetkazish
                avtomatik, qiladigan ishi yo'q.
    REQUEST  -> qo'lda bajariladigan xizmat (mentor, ariza yordami).
                Pul yechiladi, keyin admin foydalanuvchi bilan bog'lanadi.

Avval tur alohida maydonsiz, "PDF biriktirilganmi" degan qoida bilan
aniqlanardi. Bu ikki joyda yiqildi: adminkada har bir xizmat yonida fayl
yuklash tugmasi turardi (mentorga ham), ilovada esa PDF hali yuklanmagan
qo'llanma oddiy "buyurtma" bo'lib, qulfsiz va narxsiz o'tib ketardi.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, str_enum

if TYPE_CHECKING:
    from app.db.models.user import User


class ServiceKind(str, enum.Enum):
    """Xizmat nima bilan tugaydi: fayl beriladimi yoki odam bog'lanadimi."""

    FILE = "file"
    REQUEST = "request"


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

    # Sukut bo'yicha REQUEST: yangi xizmat yaratilganda unga fayl
    # biriktirilmagan bo'ladi, demak uni qulflab qo'yish noto'g'ri bo'lardi.
    kind: Mapped[ServiceKind] = mapped_column(
        str_enum(ServiceKind, "service_kind"), nullable=False, default=ServiceKind.REQUEST
    )

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


class ServiceFile(TimestampMixin, Base):
    """Xizmatga biriktirilgan PDF qo'llanma.

    Fayl BAZADA, alohida jadvalda turadi. Ikki qarorning sababi:

    Nega baza, disk emas: prod Railway'da ishlaydi, konteyner fayl tizimi
    esa har deployda toza holga qaytadi — diskka yozilgan PDF birinchi
    yangilanishda yo'qolardi. Baza esa zaxiralanadi.

    Nega alohida jadval: `admission_services` ro'yxati ilovada har ochilishda
    o'qiladi. Baytlar shu jadvalda tursa, har so'rovda megabaytlar behuda
    tortilardi. Bu yerda `data` ustuni `deferred` — uni faqat ataylab
    `undefer` qilib so'ralganda o'qiladi.
    """

    __tablename__ = "service_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique — bitta xizmatga bitta fayl. Yangisi yuklansa, eskisi o'rniga
    # yoziladi, shuning uchun "qaysi biri to'g'ri" degan savol tug'ilmaydi.
    service_id: Mapped[int] = mapped_column(
        ForeignKey("admission_services.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="application/pdf"
    )
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, deferred=True)

    # Telegram bir marta yuklangan faylni o'zida saqlaydi va `file_id` beradi.
    # Keyingi yuborishlarda baytlarni qayta jo'natmaymiz — shu id yetarli.
    # Fayl almashtirilganda bu maydon tozalanishi SHART, aks holda eski PDF
    # yuborilib qolardi.
    telegram_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    service: Mapped["AdmissionService"] = relationship(back_populates="file")

    def __str__(self) -> str:
        return self.filename


class ServiceRequest(TimestampMixin, Base):
    """Foydalanuvchining xizmatni SOTIB OLGANI.

    Yozuv paydo bo'lganda narx allaqachon balansdan yechilgan, shuning
    uchun u egalik dalili ham: PDF qo'llanma faqat shu yozuv bor odamga
    beriladi. Alohida "purchases" jadvali ataylab qilinmadi — ikkita
    jadval bir-biriga mos kelmay qolishi mumkin edi.

    PDF'li xizmat darhol yetkaziladi va DONE holatida yaratiladi; qo'lda
    bajariladigan xizmat NEW bo'lib qoladi va admin u bilan ishlaydi.
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
