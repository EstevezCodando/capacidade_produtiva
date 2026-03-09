"""Rotas de sincronizacao SAP -> sap_snapshot.

Politica de autorizacao:
    GET  /sync/status    — admin
    POST /sync/executar  — admin
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from cp.api.deps import SomenteAdmin

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncStatus(BaseModel):
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None
    ultima_execucao_status: str | None


class SyncIniciado(BaseModel):
    detail: str


@router.get("/status", summary="Status da ultima sincronizacao")
def sync_status(_: SomenteAdmin) -> SyncStatus:
    """Retorna timestamp e resultado do ultimo pipeline SAP -> sap_snapshot -> kpi."""
    # Stub — implementacao real consulta log.ingestao_execucao
    return SyncStatus(
        sap_snapshot_atualizado_em=None,
        kpi_calculado_em=None,
        ultima_execucao_status="nao_executado",
    )


@router.post("/executar", summary="Disparar sincronizacao manual", status_code=202)
def sync_executar(_: SomenteAdmin) -> SyncIniciado:
    """Aciona o pipeline completo de forma imediata (botao Sincronizar SAP)."""
    # Stub — implementacao real enfileira job APScheduler
    return SyncIniciado(detail="sincronizacao enfileirada")
