"""Sincronização SAP → sap_snapshot.

Espelha as tabelas do banco SAP para o schema sap_snapshot do banco CP.
A tabela de fatos (atividade) usa janela deslizante de 180 dias.
Todas as dimensões são sincronizadas via upsert idempotente.

Ordem do pipeline respeita dependências:
  domínios → dgeo → linha_producao → fase → subfase
  → projeto → lote → bloco → etapa → unidade_trabalho
  → atividade → perfil_producao → perfil_producao_etapa
  → perfil_producao_operador
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

_SCHEMA = "sap_snapshot"
_BATCH = 5_000


@dataclass(frozen=True)
class ResultadoTabela:
    nome: str
    lidas: int
    gravadas: int


def _ler(conn: Connection, sql: str) -> list[dict[str, object]]:
    return [dict(r._mapping) for r in conn.execute(text(sql))]


def _upsert(
    conn: Connection,
    tabela: str,
    pk: str,
    cols: list[str],
    rows: list[dict[str, object]],
) -> int:
    if not rows:
        return 0
    col_str = ", ".join(cols)
    par_str = ", ".join(f":{c}" for c in cols)
    set_str = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != pk)
    sql = text(
        f"INSERT INTO {_SCHEMA}.{tabela} ({col_str}) VALUES ({par_str}) "
        f"ON CONFLICT ({pk}) DO UPDATE SET {set_str}"
    )
    total = 0
    for i in range(0, len(rows), _BATCH):
        conn.execute(sql, rows[i : i + _BATCH])
        total += len(rows[i : i + _BATCH])
    return total


def _upsert_quando_mudou(
    conn: Connection,
    tabela: str,
    pk: str,
    cols: list[str],
    rows: list[dict[str, object]],
) -> int:
    if not rows:
        return 0
    col_str = ", ".join(cols)
    par_str = ", ".join(f":{c}" for c in cols)
    set_str = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != pk)
    where = " OR ".join(
        f"{_SCHEMA}.{tabela}.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in cols if c != pk
    )
    sql = text(
        f"INSERT INTO {_SCHEMA}.{tabela} ({col_str}) VALUES ({par_str}) "
        f"ON CONFLICT ({pk}) DO UPDATE SET {set_str} WHERE {where}"
    )
    total = 0
    for i in range(0, len(rows), _BATCH):
        conn.execute(sql, rows[i : i + _BATCH])
        total += len(rows[i : i + _BATCH])
    return total


def _sync(
    conn_sap: Connection,
    conn_cp: Connection,
    tabela_snap: str,
    sql_sap: str,
    pk: str,
    cols: list[str],
    *,
    apenas_quando_mudou: bool = False,
) -> ResultadoTabela:
    rows = _ler(conn_sap, sql_sap)
    fn = _upsert_quando_mudou if apenas_quando_mudou else _upsert
    gravadas = fn(conn_cp, tabela_snap, pk, cols, rows)
    return ResultadoTabela(tabela_snap, len(rows), gravadas)


# ---------------------------------------------------------------------------
# Funções por tabela — ordem respeita dependências
# ---------------------------------------------------------------------------


def _sync_dominio_status(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s, c, "dominio_status", "SELECT code, nome FROM dominio.status", "code", ["code", "nome"]
    )


def _sync_dominio_tipo_situacao(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "dominio_tipo_situacao",
        "SELECT code, nome FROM dominio.tipo_situacao",
        "code",
        ["code", "nome"],
    )


def _sync_dominio_tipo_etapa(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "dominio_tipo_etapa",
        "SELECT code, nome FROM dominio.tipo_etapa",
        "code",
        ["code", "nome"],
    )


def _sync_dominio_tipo_fase(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "dominio_tipo_fase",
        "SELECT code, nome, cor FROM dominio.tipo_fase",
        "code",
        ["code", "nome", "cor"],
    )


def _sync_dgeo_usuario(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "dgeo_usuario",
        "SELECT id, login, nome, nome_guerra, tipo_posto_grad_id, ativo " "FROM dgeo.usuario",
        "id",
        ["id", "login", "nome", "nome_guerra", "tipo_posto_grad_id", "ativo"],
    )


def _sync_linha_producao(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "macrocontrole_linha_producao",
        "SELECT id, nome, nome_abrev FROM macrocontrole.linha_producao",
        "id",
        ["id", "nome", "nome_abrev"],
    )


def _sync_fase(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "macrocontrole_fase",
        "SELECT id, tipo_fase_id, linha_producao_id, ordem FROM macrocontrole.fase",
        "id",
        ["id", "tipo_fase_id", "linha_producao_id", "ordem"],
    )


def _sync_subfase(s: Connection, c: Connection) -> ResultadoTabela:
    """Subfase é a dimensão-chave para todas as agregações de KPI."""
    return _sync(
        s,
        c,
        "macrocontrole_subfase",
        "SELECT id, nome, fase_id, ordem FROM macrocontrole.subfase",
        "id",
        ["id", "nome", "fase_id", "ordem"],
    )


def _sync_projeto(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "macrocontrole_projeto",
        "SELECT id, nome, nome_abrev, descricao, status_id FROM macrocontrole.projeto",
        "id",
        ["id", "nome", "nome_abrev", "descricao", "status_id"],
    )


def _sync_lote(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "macrocontrole_lote",
        "SELECT id, nome, nome_abrev, denominador_escala, linha_producao_id, "
        "projeto_id, descricao, status_id FROM macrocontrole.lote",
        "id",
        [
            "id",
            "nome",
            "nome_abrev",
            "denominador_escala",
            "linha_producao_id",
            "projeto_id",
            "descricao",
            "status_id",
        ],
    )


def _sync_bloco(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "macrocontrole_bloco",
        "SELECT id, nome, prioridade, status_id, lote_id FROM macrocontrole.bloco",
        "id",
        ["id", "nome", "prioridade", "status_id", "lote_id"],
    )


def _sync_etapa(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "macrocontrole_etapa",
        "SELECT id, tipo_etapa_id, subfase_id, lote_id, ordem FROM macrocontrole.etapa",
        "id",
        ["id", "tipo_etapa_id", "subfase_id", "lote_id", "ordem"],
    )


def _sync_unidade_trabalho(s: Connection, c: Connection) -> ResultadoTabela:
    # geom omitida: snapshot não precisa de PostGIS
    return _sync(
        s,
        c,
        "macrocontrole_unidade_trabalho",
        "SELECT id, nome, epsg, dado_producao_id, subfase_id, lote_id, bloco_id, "
        "disponivel, dificuldade, tempo_estimado_minutos, prioridade, observacao "
        "FROM macrocontrole.unidade_trabalho",
        "id",
        [
            "id",
            "nome",
            "epsg",
            "dado_producao_id",
            "subfase_id",
            "lote_id",
            "bloco_id",
            "disponivel",
            "dificuldade",
            "tempo_estimado_minutos",
            "prioridade",
            "observacao",
        ],
    )


def _sync_atividade(s: Connection, c: Connection) -> ResultadoTabela:
    """Janela deslizante: em aberto (data_fim IS NULL) ou finalizadas nos últimos 180 dias."""
    rows = _ler(
        s,
        "SELECT id, etapa_id, unidade_trabalho_id, usuario_id, tipo_situacao_id, "
        "data_inicio, data_fim, observacao "
        "FROM macrocontrole.atividade "
        "WHERE data_fim IS NULL OR data_fim >= (now() - interval '180 days')",
    )
    cols = [
        "id",
        "etapa_id",
        "unidade_trabalho_id",
        "usuario_id",
        "tipo_situacao_id",
        "data_inicio",
        "data_fim",
        "observacao",
    ]
    gravadas = _upsert_quando_mudou(c, "macrocontrole_atividade", "id", cols, rows)
    return ResultadoTabela("macrocontrole_atividade", len(rows), gravadas)


def _sync_perfil_producao(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "macrocontrole_perfil_producao",
        "SELECT id, nome FROM macrocontrole.perfil_producao",
        "id",
        ["id", "nome"],
    )


def _sync_perfil_producao_etapa(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "macrocontrole_perfil_producao_etapa",
        "SELECT id, perfil_producao_id, subfase_id, tipo_etapa_id, prioridade "
        "FROM macrocontrole.perfil_producao_etapa",
        "id",
        ["id", "perfil_producao_id", "subfase_id", "tipo_etapa_id", "prioridade"],
    )


def _sync_perfil_producao_operador(s: Connection, c: Connection) -> ResultadoTabela:
    return _sync(
        s,
        c,
        "macrocontrole_perfil_producao_operador",
        "SELECT id, usuario_id, perfil_producao_id FROM macrocontrole.perfil_producao_operador",
        "id",
        ["id", "usuario_id", "perfil_producao_id"],
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

_PIPELINE = [
    _sync_dominio_status,
    _sync_dominio_tipo_situacao,
    _sync_dominio_tipo_etapa,
    _sync_dominio_tipo_fase,
    _sync_dgeo_usuario,
    _sync_linha_producao,
    _sync_fase,
    _sync_subfase,  # dimensão-chave dos KPIs
    _sync_projeto,
    _sync_lote,
    _sync_bloco,
    _sync_etapa,
    _sync_unidade_trabalho,
    _sync_atividade,  # fatos (janela 180 dias)
    _sync_perfil_producao,
    _sync_perfil_producao_etapa,
    _sync_perfil_producao_operador,
]


def sincronizar_sap_para_snapshot(
    engine_sap: Engine,
    engine_cp: Engine,
) -> list[ResultadoTabela]:
    """Executa o pipeline completo dentro de uma única transação no CP."""
    resultados: list[ResultadoTabela] = []
    with engine_cp.begin() as conn_cp, engine_sap.connect() as conn_sap:
        for fn in _PIPELINE:
            resultados.append(fn(conn_sap, conn_cp))
    return resultados


def limpar_snapshot(engine_cp: Engine) -> int:
    """Remove atividades finalizadas há mais de 180 dias do snapshot."""
    sql = text(
        f"DELETE FROM {_SCHEMA}.macrocontrole_atividade "
        "WHERE data_fim IS NOT NULL "
        "AND data_fim < (now() - interval '180 days')"
    )
    with engine_cp.begin() as conn:
        result = conn.execute(sql)
        return int(result.rowcount or 0)
