"""Gerenciador da tabela materializada kpi.fato_ut_subfase.

A cada sync SAP → sap_snapshot, a tabela é recalculada por completo:
TRUNCATE + INSERT INTO ... SELECT.

Isso garante que o estado da tabela reflita exatamente o snapshot atual,
sem acúmulo de linhas obsoletas e sem lógica de diff.

Também expõe garantir_fato_ut_subfase(engine) para uso no bootstrap,
que cria a tabela se ainda não existir (idempotente).
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
    """Cria a tabela kpi.fato_ut_subfase se não existir (idempotente).

    Chamado no bootstrap do banco — garante que a estrutura existe antes
    do primeiro sync.
    """
    with engine_cp.begin() as conn:
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
