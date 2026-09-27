"""Admission Kit xizmatiga aniq tur: fayl yoki so'rov

Avval tur alohida maydonsiz, "PDF biriktirilganmi" degan qoida bilan
aniqlanardi. Bu ikki joyda yiqildi: adminkada har bir xizmat yonida fayl
yuklash tugmasi turardi, ilovada esa PDF hali yuklanmagan qo'llanma
qulfsiz va narxsiz oddiy "buyurtma" bo'lib o'tib ketardi.

Mavjud qatorlar: fayli bor bo'lganlar va seed bilan kelgan ikkita
qo'llanma -> FILE, qolgani -> REQUEST.

Revision ID: f3b8d24e71a6
Revises: e6a2c81d5f94
Create Date: 2026-09-27
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3b8d24e71a6"
down_revision: Union[str, None] = "e6a2c81d5f94"
branch_labels = None
depends_on = None

# Seed bilan kelgan qo'llanmalar (c1f47ab9e082). Ular ma'nosi bo'yicha
# yuklab olinadigan hujjat, hatto PDF hali yuklanmagan bo'lsa ham.
GUIDE_CODES = ("motivation_letter", "cv_guide")


def upgrade() -> None:
    kind = sa.Enum("file", "request", name="service_kind")
    kind.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "admission_services",
        # server_default — mavjud qatorlar uchun. Model darajasida sukut
        # qiymati baribir REQUEST, shuning uchun keyin ham olib tashlanmaydi:
        # bazaga to'g'ridan-to'g'ri qator qo'shilsa ham tur bo'sh qolmaydi.
        sa.Column("kind", kind, nullable=False, server_default="request"),
    )

    codes = ", ".join(f"'{code}'" for code in GUIDE_CODES)
    op.execute(
        "UPDATE admission_services SET kind = 'file' "
        "WHERE id IN (SELECT service_id FROM service_files) "
        f"OR code IN ({codes})"
    )


def downgrade() -> None:
    op.drop_column("admission_services", "kind")
    sa.Enum(name="service_kind").drop(op.get_bind(), checkfirst=True)
