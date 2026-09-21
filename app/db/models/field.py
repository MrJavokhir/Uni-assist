from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Field(TimestampMixin, Base):
    """Yo'nalishlar ma'lumotnomasi (Computer Science & IT, Law...).

    Ilgari dastur yo'nalishi erkin matn edi: bir xil yo'nalish turlicha
    yozilib ("Computer Science", "CS", dastur nomi), profil ro'yxati
    parchalanardi va moslik qidiruvi qat'iy tenglik tufayli dasturlarni
    topmasdi. Endi dastur ham, foydalanuvchi ham shu jadvaldagi yozuvga
    bog'lanadi.
    """

    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Barqaror kalit — CSV import/eksport shu bilan ishlaydi (nomlar
    # tarjima qilinishi yoki tahrirlanishi mumkin, kod esa o'zgarmaydi).
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_uz: Mapped[str] = mapped_column(String(150), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
    # Ro'yxatlarda ko'rsatish tartibi (kichigi yuqorida).
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __str__(self) -> str:
        return self.name_uz
