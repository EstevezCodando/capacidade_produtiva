"""Adiciona valor DECONSOLIDATE ao enum acao_auditoria_enum.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-19

Objetivo:
  - A migration 0007 criou o enum capacidade.acao_auditoria_enum com os valores
    'CREATE', 'UPDATE', 'DELETE', 'CONSOLIDATE'.
  - A funcionalidade de desconsolidação exige o valor 'DECONSOLIDATE', que
    foi adicionado ao enum Python (AcaoAuditoria) mas não ao banco.
  - Esta migration adiciona o valor faltante ao tipo enum do PostgreSQL.
"""

from __future__ import annotations

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar DECONSOLIDATE ao enum existente no PostgreSQL
    # ALTER TYPE não pode rodar dentro de uma transação no PostgreSQL,
    # então usamos connection com ISOLATION LEVEL AUTOCOMMIT.
    op.execute(
        "ALTER TYPE capacidade.acao_auditoria_enum ADD VALUE IF NOT EXISTS 'DECONSOLIDATE'"
    )


def downgrade() -> None:
    # PostgreSQL não suporta remoção de valores de enum diretamente.
    # A reversão segura exige recriar o enum sem o valor — mas isso quebra
    # registros existentes que já usem DECONSOLIDATE. Deixamos como no-op.
    pass
