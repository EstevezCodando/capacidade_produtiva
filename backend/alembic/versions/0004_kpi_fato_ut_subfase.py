"""Cria schema kpi e tabela kpi.fato_ut_subfase para materialização de notas e estado por UT/subfase.

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-03

A tabela é populada a cada sync SAP via TRUNCATE + INSERT INTO ... SELECT.
Chave primária natural: ut_id.
"""

from __future__ import annotations

from alembic import op
from cp.infrastructure.sap_sync.kpi_views import DDL_TABELA_FATO_UT_SUBFASE

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS kpi;")
    # DROP garante que mudanças de schema (colunas, tipos, PK) sejam aplicadas
    # mesmo em bancos que rodaram uma versão anterior desta migration.
    op.execute("DROP TABLE IF EXISTS kpi.fato_ut_subfase;")
    op.execute(DDL_TABELA_FATO_UT_SUBFASE)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kpi.fato_ut_subfase;")
    op.execute("DROP SCHEMA IF EXISTS kpi;")
