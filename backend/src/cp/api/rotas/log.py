"""Rotas de log e auditoria.

Politica de autorizacao:
    GET /log/sync    — admin
    GET /log/agenda  — admin
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from cp.api.deps import SomenteAdmin

router = APIRouter(prefix="/log", tags=["log"])


class ExecucaoSync(BaseModel):
    id: int
    iniciado_em: str
    concluido_em: str | None
    duracao_s: float | None
    status: str
    tabelas_afetadas: list[str]
    erro: str | None


class LogSyncResponse(BaseModel):
    total: int
    execucoes: list[ExecucaoSync]


@router.get("/sync", summary="Historico de execucoes do pipeline de sync")
def log_sync(
    _: SomenteAdmin,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
) -> LogSyncResponse:
    """Log de cada execucao do pipeline SAP -> sap_snapshot -> kpi: duracao, tabelas, erros."""
    return LogSyncResponse(total=0, execucoes=[])


class EventoAgenda(BaseModel):
    id: int
    acao: str
    apontamento_id: int
    usuario_id: int
    realizado_por_id: int
    realizado_por_nome: str
    em: str
    detalhe: str | None


class LogAgendaResponse(BaseModel):
    total: int
    eventos: list[EventoAgenda]


@router.get("/agenda", summary="Auditoria de apontamentos de agenda")
def log_agenda(
    _: SomenteAdmin,
    usuario_id: int | None = Query(None),
    data_inicio: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    data_fim: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
) -> LogAgendaResponse:
    """Trilha de criacao, edicao e remocao de apontamentos com usuario responsavel."""
    return LogAgendaResponse(total=0, eventos=[])
