"""Rotas de sincronizacao SAP -> sap_snapshot.

Politica de autorizacao:
    GET  /sync/status    — admin
    POST /sync/executar  — admin
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.api.deps import SomenteAdmin
from cp.application.sap_sync_service import executar_sync_sap_com_engines
from cp.application.sync_history_service import obter_ultima_execucao

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncStatus(BaseModel):
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None
    ultima_execucao_status: str | None
    ultima_execucao_em: str | None
    ultima_execucao_origem: str | None
    ultima_execucao_mensagem: str | None


class SyncIniciado(BaseModel):
    detail: str


def _obter_timestamp_snapshot(engine_cp: Engine) -> str | None:
    """Obtém timestamp da última atualização efetiva do snapshot."""
    ultima_execucao = obter_ultima_execucao(engine_cp)
    if ultima_execucao.status == "sucesso":
        return ultima_execucao.finalizado_em or ultima_execucao.iniciado_em

    sql = text("""
        SELECT MAX(data_fim) as ultima_atualizacao
        FROM sap_snapshot.macrocontrole_atividade
        WHERE data_fim IS NOT NULL
    """)
    try:
        with engine_cp.connect() as conn:
            result = conn.execute(sql)
            row = result.fetchone()
            ultima_atualizacao = cast(datetime | None, row[0] if row else None)
            if ultima_atualizacao is not None:
                return ultima_atualizacao.isoformat()
    except Exception:
        pass
    return None


def _obter_timestamp_kpi(engine_cp: Engine) -> str | None:
    """Obtém timestamp do último cálculo de KPI a partir da última sync concluída."""
    sql = text("""
        SELECT COUNT(*) as total FROM kpi.estado_ut
    """)
    try:
        with engine_cp.connect() as conn:
            result = conn.execute(sql)
            row = result.fetchone()
            if row and row.total > 0:
                ultima_execucao = obter_ultima_execucao(engine_cp)
                return ultima_execucao.finalizado_em or ultima_execucao.iniciado_em
    except Exception:
        pass
    return None


def _executar_sync_background(engine_sap: Engine, engine_cp: Engine) -> None:
    """Executa sincronização em background persistindo histórico no banco."""
    executar_sync_sap_com_engines(engine_sap, engine_cp, origem="api")


@router.get("/status", summary="Status da ultima sincronizacao")
def sync_status(_: SomenteAdmin, request: Request) -> SyncStatus:
    """Retorna timestamps e o resultado da última execução do pipeline."""
    engine_cp = request.app.state.engine_cp
    ultima_execucao = obter_ultima_execucao(engine_cp)

    return SyncStatus(
        sap_snapshot_atualizado_em=_obter_timestamp_snapshot(engine_cp),
        kpi_calculado_em=_obter_timestamp_kpi(engine_cp),
        ultima_execucao_status=ultima_execucao.status,
        ultima_execucao_em=ultima_execucao.finalizado_em or ultima_execucao.iniciado_em,
        ultima_execucao_origem=ultima_execucao.origem,
        ultima_execucao_mensagem=ultima_execucao.mensagem,
    )


@router.post("/executar", summary="Disparar sincronizacao manual", status_code=202)
def sync_executar(
    _: SomenteAdmin,
    request: Request,
    background_tasks: BackgroundTasks,
) -> SyncIniciado:
    """Aciona o pipeline completo de forma imediata."""
    engine_sap = request.app.state.engine_sap
    engine_cp = request.app.state.engine_cp
    background_tasks.add_task(_executar_sync_background, engine_sap, engine_cp)
    return SyncIniciado(detail="sincronização enfileirada")
