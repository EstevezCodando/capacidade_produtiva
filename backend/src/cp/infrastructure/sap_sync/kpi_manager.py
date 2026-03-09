"""Gerenciador das tabelas materializadas do schema kpi.

Pipeline de materialização (ordem estrita — cada tabela depende da anterior):

  1. kpi.fluxo_ut          — ciclo + pivot das atividades vigentes
  2. kpi.participantes_ut  — participantes normalizados por papel
  3. kpi.validacao_fluxo   — fluxo fechado ou não
  4. kpi.validacao_nota    — nota extraída e validada
  5. kpi.pontos_usuario    — pontos calculados por usuário/papel
  6. kpi.estado_ut         — estado consolidado da UT

Todas as tabelas são recalculadas via TRUNCATE + INSERT dentro da mesma
transação do pipeline de sync — se qualquer etapa falhar, nenhuma tabela
é alterada (atomicidade garantida pelo caller).

O INSERT usa lista explícita de colunas lida do information_schema, tornando
a materialização imune à ordem das colunas no SELECT.

garantir_tabelas_kpi(engine): cria/recria todas as tabelas com DDL atual.
materializar_kpi(conn):        executa o pipeline completo.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from cp.infrastructure.sap_sync.kpi_tables import TABELAS_KPI

_logger = logging.getLogger(__name__)
_SCHEMA = "kpi"


def garantir_tabelas_kpi(engine_cp: Engine) -> None:
    """Recria todas as tabelas kpi.* com o DDL atual (idempotente).

    Usa DROP TABLE IF EXISTS + CREATE para garantir que mudanças de schema
    (novas colunas, tipos alterados, chave primária) sejam sempre aplicadas,
    mesmo em bancos que já tinham uma versão anterior das tabelas.

    Chamado no bootstrap do banco — seguro rodar a qualquer momento.
    """
    with engine_cp.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA};"))
        # Ordem inversa para DROP (dependentes primeiro)
        for nome, _ddl, _sql in reversed(TABELAS_KPI):
            conn.execute(text(f"DROP TABLE IF EXISTS {_SCHEMA}.{nome} CASCADE;"))
        for nome, ddl, _sql in TABELAS_KPI:
            _logger.debug("Criando tabela %s.%s", _SCHEMA, nome)
            conn.execute(text(ddl))


def _colunas_da_tabela(conn: Connection, tabela: str) -> list[str]:
    """Retorna a lista de colunas de kpi.<tabela> na ordem do DDL.

    Lido do information_schema — garante que o INSERT use a ordem real
    da tabela no banco, independente da ordem do SELECT.
    """
    rows = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_schema = :schema AND table_name = :tabela ORDER BY ordinal_position"),
        {"schema": _SCHEMA, "tabela": tabela},
    ).fetchall()
    return [r[0] for r in rows]


def materializar_kpi(conn_cp: Connection) -> dict[str, int]:
    """Executa o pipeline completo de materialização KPI.

    Usa INSERT INTO tabela(col1, col2, ...) SELECT col1, col2, ...
    mapeando por nome via information_schema — imune à ordem das colunas.

    Ordem estrita: fluxo_ut -> participantes_ut -> validacao_fluxo ->
                   validacao_nota -> pontos_usuario -> estado_ut.

    Chamado no final do pipeline de sync, dentro da transação existente.
    Retorna dict {nome_tabela: linhas_inseridas}.
    """
    resultado: dict[str, int] = {}
    for nome, _ddl, sql in TABELAS_KPI:
        tabela = f"{_SCHEMA}.{nome}"
        conn_cp.execute(text(f"TRUNCATE {tabela};"))

        colunas = _colunas_da_tabela(conn_cp, nome)
        lista = ", ".join(colunas)
        r = conn_cp.execute(text(f"INSERT INTO {tabela} ({lista})\nSELECT {lista} FROM ({sql}) AS _kpi_src"))
        linhas = int(r.rowcount or 0)
        resultado[nome] = linhas
        _logger.debug("Materializado %s: %d linhas", tabela, linhas)
    return resultado
