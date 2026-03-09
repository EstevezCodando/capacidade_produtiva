"""Rotas de relatorios e exportacao.

Politica de autorizacao:
    GET /relatorios/capacidade        — autenticado
    GET /relatorios/producao          — autenticado
    GET /relatorios/progresso-blocos  — autenticado
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from cp.api.deps import UsuarioLogado

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


class RelatorioCapacidadeItem(BaseModel):
    usuario_id: int
    nome: str
    horas_planejadas_min: int
    horas_realizadas_min: int
    saldo_min: int


class RelatorioCapacidadeResponse(BaseModel):
    data_inicio: str
    data_fim: str
    itens: list[RelatorioCapacidadeItem]


@router.get("/capacidade", summary="Relatorio de capacidade por operador")
def relatorio_capacidade(
    _: UsuarioLogado,
    data_inicio: str = Query(..., description="ISO date YYYY-MM-DD"),
    data_fim: str = Query(..., description="ISO date YYYY-MM-DD"),
    usuario_id: int | None = Query(None),
) -> RelatorioCapacidadeResponse:
    """Horas planejadas vs realizadas por operador no periodo. Aba Exportar."""
    return RelatorioCapacidadeResponse(data_inicio=data_inicio, data_fim=data_fim, itens=[])


class RelatorioProducaoItem(BaseModel):
    usuario_id: int
    nome: str
    pontos_executor: float
    pontos_revisor: float
    pontos_corretor: float
    uts_concluidas: int


class RelatorioProducaoResponse(BaseModel):
    data_inicio: str
    data_fim: str
    itens: list[RelatorioProducaoItem]


@router.get("/producao", summary="Relatorio de producao por operador")
def relatorio_producao(
    _: UsuarioLogado,
    data_inicio: str = Query(..., description="ISO date YYYY-MM-DD"),
    data_fim: str = Query(..., description="ISO date YYYY-MM-DD"),
    usuario_id: int | None = Query(None),
) -> RelatorioProducaoResponse:
    """Pontos e UTs concluidas por operador no periodo, com distribuicao por ciclo e papel."""
    return RelatorioProducaoResponse(data_inicio=data_inicio, data_fim=data_fim, itens=[])


class SubfaseProgresso(BaseModel):
    subfase_id: int
    subfase_nome: str
    progresso: float
    pontos_total: float
    pontos_concluidos: float


class BlocoProgresso(BaseModel):
    bloco_id: int
    bloco_nome: str
    progresso: float
    subfases: list[SubfaseProgresso]


class RelatorioProgressoBlocosResponse(BaseModel):
    projeto_id: int
    projeto_nome: str
    sap_snapshot_atualizado_em: str | None
    blocos: list[BlocoProgresso]


@router.get("/progresso-blocos", summary="Progresso por bloco e subfase")
def relatorio_progresso_blocos(
    _: UsuarioLogado,
    projeto_id: int = Query(...),
) -> RelatorioProgressoBlocosResponse:
    """Avanco percentual por bloco e subfase. Aba Blocos do Projeto."""
    return RelatorioProgressoBlocosResponse(
        projeto_id=projeto_id,
        projeto_nome="",
        sap_snapshot_atualizado_em=None,
        blocos=[],
    )
