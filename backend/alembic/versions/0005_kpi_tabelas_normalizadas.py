"""Substitui kpi.fato_ut_subfase pelas 6 tabelas normalizadas do pipeline KPI.

Revision ID: 0005
Revises: 0004
Create Date: 2025-01-04

Motivação:
  A tabela monolítica fato_ut_subfase misturava 6 responsabilidades distintas
  (detecção de ciclo, participantes, validação de fluxo, validação de nota,
  cálculo de pontos e estado consolidado) num único SELECT de 700+ linhas.

  A refatoração separa cada responsabilidade numa tabela dedicada, tornando
  o pipeline auditável, testável e extensível independentemente.

Novas tabelas:
  kpi.fluxo_ut          — ciclo detectado + atividades vigentes (pivot)
  kpi.participantes_ut  — participantes normalizados por papel
  kpi.validacao_fluxo   — fluxo fechado / etapa bloqueante
  kpi.validacao_nota    — nota extraída e validada
  kpi.pontos_usuario    — pontos calculados por (ut, papel)
  kpi.estado_ut         — estado consolidado (substituto direto de fato_ut_subfase)
"""

from __future__ import annotations

from alembic import op
from cp.infrastructure.sap_sync.kpi_tables import TABELAS_KPI

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS kpi;")
    # Remove tabela monolítica (se existir de uma run anterior da 0004)
    op.execute("DROP TABLE IF EXISTS kpi.fato_ut_subfase CASCADE;")
    # Remove novas tabelas (se existirem de run parcial)
    for nome, _ddl, _sql in reversed(TABELAS_KPI):
        op.execute(f"DROP TABLE IF EXISTS kpi.{nome} CASCADE;")
    # Cria novas tabelas na ordem correta
    for _nome, ddl, _sql in TABELAS_KPI:
        op.execute(ddl)


def downgrade() -> None:
    for nome, _ddl, _sql in reversed(TABELAS_KPI):
        op.execute(f"DROP TABLE IF EXISTS kpi.{nome} CASCADE;")
    # Não recria fato_ut_subfase — downgrade para 0004 é destrutivo
    # (seria necessário recriar a tabela monolítica manualmente)
