"""Adiciona teto de sexta-feira e ajusta default do teto extra.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-13

Objetivo:
  - Adicionar coluna minutos_sexta_default à tabela parametro_capacidade
    para distinguir o teto de sexta-feira (4h = 240 min) do teto de
    segunda a quinta (6h = 360 min).
  - O default de banco para minutos_extra_maximo_default permanece 240
    para linhas existentes; novos parâmetros criados pelo código usarão
    o novo default Python de 600 min (10h).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parametro_capacidade",
        sa.Column(
            "minutos_sexta_default",
            sa.Integer(),
            nullable=False,
            server_default="240",
        ),
        schema="capacidade",
    )


def downgrade() -> None:
    op.drop_column("parametro_capacidade", "minutos_sexta_default", schema="capacidade")
