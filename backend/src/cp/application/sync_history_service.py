from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class SyncExecucaoInfo:
    id: int | None
    iniciado_em: str | None
    finalizado_em: str | None
    status: str | None
    origem: str | None
    mensagem: str | None


_SQL_GARANTIR_TABELA = text(
    """
    CREATE SCHEMA IF NOT EXISTS log;

    CREATE TABLE IF NOT EXISTS log.sync_execucao (
        id BIGSERIAL PRIMARY KEY,
        iniciado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        finalizado_em TIMESTAMPTZ NULL,
        status VARCHAR(32) NOT NULL,
        origem VARCHAR(32) NOT NULL,
        mensagem TEXT NULL
    );

    CREATE INDEX IF NOT EXISTS ix_sync_execucao_iniciado_em
        ON log.sync_execucao (iniciado_em DESC);
    """
)



def garantir_tabela_sync_execucao(engine_cp: Engine) -> None:
    with engine_cp.begin() as conn:
        conn.execute(_SQL_GARANTIR_TABELA)



def registrar_inicio_sync(engine_cp: Engine, origem: str) -> int:
    garantir_tabela_sync_execucao(engine_cp)
    with engine_cp.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO log.sync_execucao (status, origem, mensagem)
                VALUES ('executando', :origem, 'Sincronização em andamento')
                RETURNING id
                """
            ),
            {"origem": origem},
        )
        row = result.fetchone()
        if row is None:
            raise RuntimeError("INSERT INTO sync_execucao não retornou id")
        return int(row.id)



def finalizar_sync(
    engine_cp: Engine,
    execucao_id: int,
    *,
    status: str,
    mensagem: str | None,
) -> None:
    garantir_tabela_sync_execucao(engine_cp)
    with engine_cp.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE log.sync_execucao
                   SET finalizado_em = NOW(),
                       status = :status,
                       mensagem = :mensagem
                 WHERE id = :execucao_id
                """
            ),
            {
                "execucao_id": execucao_id,
                "status": status,
                "mensagem": mensagem,
            },
        )



def obter_ultima_execucao(engine_cp: Engine) -> SyncExecucaoInfo:
    garantir_tabela_sync_execucao(engine_cp)
    with engine_cp.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    id,
                    iniciado_em,
                    finalizado_em,
                    status,
                    origem,
                    mensagem
                FROM log.sync_execucao
                ORDER BY id DESC
                LIMIT 1
                """
            )
        ).mappings().first()

    if row is None:
        return SyncExecucaoInfo(
            id=None,
            iniciado_em=None,
            finalizado_em=None,
            status=None,
            origem=None,
            mensagem=None,
        )

    return SyncExecucaoInfo(
        id=int(row["id"]),
        iniciado_em=_iso(row.get("iniciado_em")),
        finalizado_em=_iso(row.get("finalizado_em")),
        status=_str_or_none(row.get("status")),
        origem=_str_or_none(row.get("origem")),
        mensagem=_str_or_none(row.get("mensagem")),
    )



def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None



def _str_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None
