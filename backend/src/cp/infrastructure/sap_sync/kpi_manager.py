"""Gerenciador da tabela materializada kpi.fato_ut_subfase.

A cada sync SAP → sap_snapshot, a tabela é recalculada por completo:
TRUNCATE + INSERT INTO ... SELECT.

Isso garante que o estado da tabela reflita exatamente o snapshot atual,
sem acúmulo de linhas obsoletas e sem lógica de diff.

Também expõe garantir_fato_ut_subfase(engine) para uso no bootstrap,
que recria a tabela se o schema mudou (DROP + CREATE, idempotente).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from cp.infrastructure.sap_sync.kpi_views import (
    DDL_TABELA_FATO_UT_SUBFASE,
    SQL_SELECT_FATO_UT_SUBFASE,
)

_TABELA = "kpi.fato_ut_subfase"


def garantir_fato_ut_subfase(engine_cp: Engine) -> None:
    """Recria kpi.fato_ut_subfase com o DDL atual (idempotente).

    Usa DROP TABLE IF EXISTS antes do CREATE para garantir que mudanças de
    schema (colunas, tipos, chave primária) sejam sempre aplicadas, mesmo
    em bancos que rodaram uma versão anterior desta migration.

    Chamado no bootstrap do banco — safe para rodar a qualquer momento.
    """
    with engine_cp.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS kpi;"))
        conn.execute(text(f"DROP TABLE IF EXISTS {_TABELA};"))
        conn.execute(text(DDL_TABELA_FATO_UT_SUBFASE))


def materializar_fato_ut_subfase(conn_cp: Connection) -> int:
    """Recalcula kpi.fato_ut_subfase via TRUNCATE + INSERT INTO ... SELECT.

    Chamado no final do pipeline de sync, dentro da mesma transação dos
    snapshots — se o sync falhar, a tabela não é alterada.

    Retorna o número de linhas inseridas.
    """
    conn_cp.execute(text(f"TRUNCATE {_TABELA}"))
    result = conn_cp.execute(text(f"INSERT INTO {_TABELA}\n{SQL_SELECT_FATO_UT_SUBFASE}"))
    return int(result.rowcount or 0)
