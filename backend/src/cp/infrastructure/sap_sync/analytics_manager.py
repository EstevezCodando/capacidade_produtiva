"""Gerenciador das views analíticas do schema sap_analytics.

Responsabilidade única: garantir que as views existam e estejam atualizadas.
Chamado em dois momentos do ciclo de vida:
  1. Bootstrap do banco (ao subir o sistema pela primeira vez ou após deploy)
  2. Após cada ingestão do pipeline SAP → sap_snapshot

Estratégia DROP + CREATE (em vez de CREATE OR REPLACE):
  O PostgreSQL não permite que CREATE OR REPLACE VIEW altere a assinatura de
  uma view já existente (ordem ou tipo das colunas). Para suportar evoluções
  de schema sem exigir intervenção manual, fazemos DROP IF EXISTS ... CASCADE
  seguido de CREATE VIEW dentro da mesma transação. O CASCADE garante que
  views dependentes (ex.: vw_ut_atividade depende de vw_ut_enriquecida) sejam
  derrubadas e recriadas na ordem correta.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from cp.infrastructure.sap_sync.analytics_views import (
    DDL_SCHEMA,
    NOMES_DAS_VIEWS,
    TODAS_AS_VIEWS,
)


def garantir_views_analytics(engine_cp: Engine) -> None:
    """Cria o schema e aplica todas as views analíticas (idempotente).

    Faz DROP IF EXISTS CASCADE + CREATE em transação única.
    Seguro para rodar múltiplas vezes e para mudanças de assinatura.
    """
    with engine_cp.begin() as conn:
        _aplicar_views(conn)


def atualizar_views_analytics(conn_cp: Connection) -> None:
    """Re-aplica as views dentro de uma conexão/transação já existente.

    Projetado para ser chamado no final do pipeline de sync, aproveitando
    a mesma transação e evitando overhead de abertura de nova conexão.
    """
    _aplicar_views(conn_cp)


def _aplicar_views(conn: Connection) -> None:
    conn.execute(text(DDL_SCHEMA))
    _derrubar_views(conn)
    for ddl in TODAS_AS_VIEWS:
        conn.execute(text(ddl))


def _derrubar_views(conn: Connection) -> None:
    """Remove todas as views em ordem inversa de dependência (CASCADE cobre o resto)."""
    for nome in NOMES_DAS_VIEWS:
        conn.execute(text(f"DROP VIEW IF EXISTS {nome} CASCADE"))
