"""Admission Kit xizmatini do'st taklif qilib ochish

Uch o'zgarish:

1. `admission_services.unlock_invites` — shuncha tasdiqlangan taklifi bor
   odam xizmatni pulsiz oladi. 0 — bunday imkoniyat yo'q.

2. `service_requests.unlocked_by_invites` — xizmat pulga emas, taklif
   bilan ochilganini yozib qo'yadi. Pulga tegishli qaror bo'lgani uchun
   izsiz qolmasligi kerak: balans tarixida yechim ko'rinmaydi.

3. `users.referral_rewarded` -> `referral_confirmed`. Bayroqning ma'nosi
   "pul berildi" emas, "taklif tasdiqlandi" (odam kanalga a'zo bo'ldi).
   Ilgari u faqat pul berilganda yoqilardi va mukofot 0 ga qo'yilsa
   taklif hech qayerda hisobga olinmay qolardi — endi u xizmat ochish
   uchun ham sanaladi.

Revision ID: e5c1b47d920f
Revises: a7c5e92b14d8
Create Date: 2026-10-03
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5c1b47d920f"
down_revision: Union[str, None] = "a7c5e92b14d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admission_services",
        sa.Column("unlock_invites", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "service_requests",
        sa.Column(
            "unlocked_by_invites", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    # Nomi o'zgaradi, ma'lumot joyida qoladi: allaqachon tasdiqlangan
    # takliflar yo'qolmasligi kerak.
    op.alter_column("users", "referral_rewarded", new_column_name="referral_confirmed")


def downgrade() -> None:
    op.alter_column("users", "referral_confirmed", new_column_name="referral_rewarded")
    op.drop_column("service_requests", "unlocked_by_invites")
    op.drop_column("admission_services", "unlock_invites")
