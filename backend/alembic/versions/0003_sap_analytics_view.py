"""Cria schema sap_analytics com as views de enriquecimento (UT e Atividade).

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-02

Views criadas:
  - vw_ut_enriquecida        : UT + hierarquia completa (projeto/lote/bloco/subfase/fase)
  - vw_atividade_enriquecida : atividade + etapa/tipo_etapa/tipo_situacao/usuario/is_finalizada
  - vw_ut_atividade          : join completo UT + atividade (critério 4 do sprint)
"""

from __future__ import annotations

from alembic import op
from cp.infrastructure.sap_sync.analytics_views import (
    DDL_SCHEMA,
    DDL_VW_ATIVIDADE_ENRIQUECIDA,
    DDL_VW_UT_ATIVIDADE,
    DDL_VW_UT_ENRIQUECIDA,
)

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(DDL_SCHEMA)
    op.execute(DDL_VW_UT_ENRIQUECIDA)
    op.execute(DDL_VW_ATIVIDADE_ENRIQUECIDA)
    op.execute(DDL_VW_UT_ATIVIDADE)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS sap_analytics.vw_ut_atividade CASCADE;")
    op.execute("DROP VIEW IF EXISTS sap_analytics.vw_atividade_enriquecida CASCADE;")
    op.execute("DROP VIEW IF EXISTS sap_analytics.vw_ut_enriquecida CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS sap_analytics CASCADE;")
