"""Adiciona soft delete em agenda e mantém múltiplos lançamentos por dia.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agenda_prevista_admin",
        sa.Column("em_uso", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema="capacidade",
    )
    op.add_column(
        "agenda_lancamento",
        sa.Column("em_uso", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema="capacidade",
    )
        op.add_column(
        "agenda_prevista_admin",
        sa.Column("consolidado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema="capacidade",
    )
    op.add_column(
        "agenda_lancamento",
        sa.Column("consolidado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema="capacidade",
    )

    op.execute("ALTER TABLE capacidade.agenda_prevista_admin DROP CONSTRAINT IF EXISTS uq_agenda_prevista_usuario_data_bloco")
    op.create_index("ix_agenda_prevista_em_uso", "agenda_prevista_admin", ["em_uso"], schema="capacidade")
    op.create_index("ix_agenda_lancamento_em_uso", "agenda_lancamento", ["em_uso"], schema="capacidade")
    op.create_index("ix_agenda_prevista_consolidado", "agenda_prevista_admin", ["consolidado"], schema="capacidade")
    op.create_index("ix_agenda_lancamento_consolidado", "agenda_lancamento", ["consolidado"], schema="capacidade")

def downgrade() -> None:
    op.drop_index("ix_agenda_lancamento_em_uso", table_name="agenda_lancamento", schema="capacidade")
    op.drop_index("ix_agenda_prevista_em_uso", table_name="agenda_prevista_admin", schema="capacidade")
    op.execute(
        "ALTER TABLE capacidade.agenda_prevista_admin ADD CONSTRAINT uq_agenda_prevista_usuario_data_bloco UNIQUE (usuario_id, data, bloco_id)"
    )
    op.drop_column("agenda_lancamento", "em_uso", schema="capacidade")
    op.drop_column("agenda_prevista_admin", "em_uso", schema="capacidade")
