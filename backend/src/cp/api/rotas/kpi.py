"""Rotas de KPI e progresso de producao.

Politica de autorizacao:
    GET /kpi/projetos              — autenticado
    GET /kpi/projetos/{id}         — autenticado
    GET /kpi/subfase/{id}          — autenticado
    GET /kpi/uts/{id}              — autenticado
    GET /kpi/inconsistencias       — admin
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from cp.api.deps import SomenteAdmin, UsuarioLogado

router = APIRouter(prefix="/kpi", tags=["kpi"])


class KpiProjeto(BaseModel):
    projeto_id: int
    nome: str
    progresso: float | None
    pontos_total: float
    pontos_concluidos: float
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None


class KpiProjetosResponse(BaseModel):
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None
    projetos: list[KpiProjeto]


@router.get("/projetos", summary="KPI agregado por projeto")
def kpi_projetos(_: UsuarioLogado) -> KpiProjetosResponse:
    """Progresso percentual, pontos totais e concluidos por projeto ativo."""
    return KpiProjetosResponse(
        sap_snapshot_atualizado_em=None,
        kpi_calculado_em=None,
        projetos=[],
    )


class KpiSubfase(BaseModel):
    subfase_id: int
    subfase_nome: str
    progresso: float | None
    pontos_total: float
    pontos_concluidos: float


class KpiBloco(BaseModel):
    bloco_id: int
    bloco_nome: str
    subfases: list[KpiSubfase]


class KpiProjetoDetalhe(BaseModel):
    projeto_id: int
    projeto_nome: str
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None
    blocos: list[KpiBloco]


@router.get("/projetos/{projeto_id}", summary="KPI do projeto por bloco e subfase")
def kpi_projeto_detalhe(projeto_id: int, _: UsuarioLogado) -> KpiProjetoDetalhe:
    """Drill-down do projeto: progresso por bloco e subfase."""
    return KpiProjetoDetalhe(
        projeto_id=projeto_id,
        projeto_nome="",
        sap_snapshot_atualizado_em=None,
        kpi_calculado_em=None,
        blocos=[],
    )


class KpiUt(BaseModel):
    ut_id: int
    estado_ut_subfase: str
    ciclo_modelo: str
    nota_qualidade: int | None
    ocorrencia: str
    pontos_executor: float | None
    pontos_revisor: float | None
    pontos_corretor: float | None
    nome_executor: str | None
    nome_revisor: str | None
    nome_corretor: str | None
    data_inicio_fluxo: str | None
    data_fim_fluxo: str | None


class KpiSubfaseDetalhe(BaseModel):
    subfase_id: int
    subfase_nome: str
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None
    uts: list[KpiUt]


@router.get("/subfase/{subfase_id}", summary="UTs de uma subfase")
def kpi_subfase(subfase_id: int, _: UsuarioLogado) -> KpiSubfaseDetalhe:
    """Listagem completa das UTs da subfase com estado, ciclo, nota e pontos."""
    return KpiSubfaseDetalhe(
        subfase_id=subfase_id,
        subfase_nome="",
        sap_snapshot_atualizado_em=None,
        kpi_calculado_em=None,
        uts=[],
    )


class KpiUtDetalhe(BaseModel):
    ut_id: int
    ciclo_modelo: str
    estado_ut_subfase: str
    concluida: bool
    nota_qualidade: int | None
    texto_qualidade: str | None
    ocorrencia: str
    data_inicio_fluxo: str | None
    data_fim_fluxo: str | None
    pontos_ut: float | None
    pontos_executor: float | None
    pontos_revisor: float | None
    pontos_corretor: float | None
    nome_executor: str | None
    nome_revisor: str | None
    nome_corretor: str | None
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None


@router.get("/uts/{ut_id}", summary="Detalhe completo de uma UT")
def kpi_ut(ut_id: int, _: UsuarioLogado) -> KpiUtDetalhe:
    """Estado completo da UT: ciclo, fluxo, nota, participantes e pontos."""
    return KpiUtDetalhe(
        ut_id=ut_id,
        ciclo_modelo="",
        estado_ut_subfase="",
        concluida=False,
        nota_qualidade=None,
        texto_qualidade=None,
        ocorrencia="",
        data_inicio_fluxo=None,
        data_fim_fluxo=None,
        pontos_ut=None,
        pontos_executor=None,
        pontos_revisor=None,
        pontos_corretor=None,
        nome_executor=None,
        nome_revisor=None,
        nome_corretor=None,
        sap_snapshot_atualizado_em=None,
        kpi_calculado_em=None,
    )


class Inconsistencia(BaseModel):
    ut_id: int
    ocorrencia: str
    projeto_nome: str | None
    subfase_nome: str | None
    ciclo_modelo: str
    nome_executor: str | None


class InconsistenciasResponse(BaseModel):
    total: int
    sap_snapshot_atualizado_em: str | None
    itens: list[Inconsistencia]


@router.get("/inconsistencias", summary="Alertas e inconsistencias de nota e ciclo")
def kpi_inconsistencias(_: SomenteAdmin) -> InconsistenciasResponse:
    """UTs com NOTA_AUSENTE, NOTA_INVALIDA, INCONSISTENTE_CICLO ou INCONSISTENTE_DIFICULDADE."""
    return InconsistenciasResponse(
        total=0,
        sap_snapshot_atualizado_em=None,
        itens=[],
    )
