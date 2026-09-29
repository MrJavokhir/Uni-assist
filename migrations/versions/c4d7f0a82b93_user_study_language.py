"""Filtrga o'qish tili qo'shildi

`users.study_language` da `programs.language_of_instruction` bilan bir xil
kanonik inglizcha nom saqlanadi ("English", "German"), chunki filtr aynan
shu ustun bilan solishtiriladi. NULL = farqi yo'q.

Revision ID: c4d7f0a82b93
Revises: b9e4a2c37f15
Create Date: 2026-09-29
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d7f0a82b93"
down_revision: Union[str, None] = "b9e4a2c37f15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("study_language", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "study_language")
