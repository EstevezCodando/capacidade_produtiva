"""Rotas de sincronizacao SAP -> sap_snapshot.

Politica de autorizacao:
    GET  /sync/status    — admin
    POST /sync/executar  — admin
"""

from __future__ import annotations

<<<<<<< HEAD
from fastapi import APIRouter
from pydantic import BaseModel

from cp.api.deps import SomenteAdmin

router = APIRouter(prefix="/sync", tags=["sync"])
=======
import logging
from datetime import datetime
from typing import cast

from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.api.deps import SomenteAdmin
from cp.infrastructure.sap_sync.sync import sincronizar_sap_para_snapshot

router = APIRouter(prefix="/sync", tags=["sync"])
_logger = logging.getLogger(__name__)

# Estado global simples para rastrear última execução
_ultima_execucao: dict[str, str | None] = {
    "timestamp": None,
    "status": "nao_executado",
}
>>>>>>> feature/front


class SyncStatus(BaseModel):
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None
    ultima_execucao_status: str | None


class SyncIniciado(BaseModel):
    detail: str


<<<<<<< HEAD
@router.get("/status", summary="Status da ultima sincronizacao")
def sync_status(_: SomenteAdmin) -> SyncStatus:
    """Retorna timestamp e resultado do ultimo pipeline SAP -> sap_snapshot -> kpi."""
    # Stub — implementacao real consulta log.ingestao_execucao
    return SyncStatus(
        sap_snapshot_atualizado_em=None,
        kpi_calculado_em=None,
        ultima_execucao_status="nao_executado",
=======
def _obter_timestamp_snapshot(engine_cp: Engine) -> str | None:
    """Obtém timestamp da última atualização do snapshot."""
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
    """Obtém timestamp do último cálculo de KPI verificando se tabelas têm dados."""
    sql = text("""
        SELECT COUNT(*) as total FROM kpi.estado_ut
    """)
    try:
        with engine_cp.connect() as conn:
            result = conn.execute(sql)
            row = result.fetchone()
            if row and row.total > 0:
                timestamp = _ultima_execucao.get("timestamp")
                return timestamp if isinstance(timestamp, str) else None
    except Exception:
        pass
    return None


def _executar_sync_background(engine_sap: Engine, engine_cp: Engine) -> None:
    """Executa sincronização em background."""
    global _ultima_execucao
    try:
        _logger.info("Iniciando sincronização SAP -> sap_snapshot")
        resultados = sincronizar_sap_para_snapshot(engine_sap, engine_cp)

        total_lidas = sum(r.lidas for r in resultados)
        total_gravadas = sum(r.gravadas for r in resultados)

        _ultima_execucao = {
            "timestamp": datetime.now().isoformat(),
            "status": "sucesso",
        }
        _logger.info(
            "Sincronização concluída: %d registros lidos, %d gravados",
            total_lidas,
            total_gravadas,
        )
    except Exception as e:
        _ultima_execucao = {
            "timestamp": datetime.now().isoformat(),
            "status": f"erro: {e}",
        }
        _logger.exception("Erro na sincronização: %s", e)


@router.get("/status", summary="Status da ultima sincronizacao")
def sync_status(_: SomenteAdmin, request: Request) -> SyncStatus:
    """Retorna timestamp e resultado do ultimo pipeline SAP -> sap_snapshot -> kpi."""
    engine_cp = request.app.state.engine_cp

    return SyncStatus(
        sap_snapshot_atualizado_em=_obter_timestamp_snapshot(engine_cp),
        kpi_calculado_em=_obter_timestamp_kpi(engine_cp),
        ultima_execucao_status=_ultima_execucao.get("status", "nao_executado"),
>>>>>>> feature/front
    )


@router.post("/executar", summary="Disparar sincronizacao manual", status_code=202)
<<<<<<< HEAD
def sync_executar(_: SomenteAdmin) -> SyncIniciado:
    """Aciona o pipeline completo de forma imediata (botao Sincronizar SAP)."""
    # Stub — implementacao real enfileira job APScheduler
    return SyncIniciado(detail="sincronizacao enfileirada")
=======
def sync_executar(
    _: SomenteAdmin,
    request: Request,
    background_tasks: BackgroundTasks,
) -> SyncIniciado:
    """Aciona o pipeline completo de forma imediata (botao Sincronizar SAP)."""
    engine_sap = request.app.state.engine_sap
    engine_cp = request.app.state.engine_cp

    # Executa em background para não bloquear a requisição
    background_tasks.add_task(_executar_sync_background, engine_sap, engine_cp)

    return SyncIniciado(detail="sincronização enfileirada")
>>>>>>> feature/front
