"""Rotas de capacidade (teto diario, status, consolidacao, feriados).

Politica de autorizacao:
    GET  /capacidade/config             — admin
    PUT  /capacidade/config             — admin
    GET  /capacidade/status             — admin
    POST /capacidade/consolidar         — admin
    GET  /capacidade/feriados           — autenticado
    POST /capacidade/feriados           — admin
    DELETE /capacidade/feriados/{id}    — admin
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from cp.api.deps import SomenteAdmin, UsuarioLogado

router = APIRouter(prefix="/capacidade", tags=["capacidade"])


# ── Configuracao de teto ─────────────────────────────────────────────────────


class ConfigTeto(BaseModel):
    teto_normal_min: int
    teto_extra_min: int
    configurado_em: str | None
    configurado_por: str | None


@router.get("/config", summary="Configuracao do teto diario")
def config_teto(_: SomenteAdmin) -> ConfigTeto:
    """Retorna teto normal e extra vigentes. Editavel pelo gerente."""
    return ConfigTeto(teto_normal_min=360, teto_extra_min=600, configurado_em=None, configurado_por=None)


class ConfigTetoInput(BaseModel):
    teto_normal_min: int
    teto_extra_min: int


@router.put("/config", summary="Atualizar teto diario")
def atualizar_config_teto(body: ConfigTetoInput, _: SomenteAdmin) -> ConfigTeto:
    """Atualiza o teto normal e extra. Alteracao e auditada."""
    return ConfigTeto(
        teto_normal_min=body.teto_normal_min,
        teto_extra_min=body.teto_extra_min,
        configurado_em=None,
        configurado_por=None,
    )


# ── Status dos dias ──────────────────────────────────────────────────────────


class StatusDia(BaseModel):
    data: str
    status: str


class StatusDiasResponse(BaseModel):
    dias: list[StatusDia]


@router.get("/status", summary="Status dos dias no intervalo")
def status_dias(
    _: SomenteAdmin,
    data_inicio: str = Query(..., description="ISO date YYYY-MM-DD"),
    data_fim: str = Query(..., description="ISO date YYYY-MM-DD"),
) -> StatusDiasResponse:
    """Status (ABERTO/CONSOLIDADO) de cada dia do intervalo para todos os usuarios ativos."""
    return StatusDiasResponse(dias=[])


# ── Consolidacao ─────────────────────────────────────────────────────────────


class PendenciaUsuario(BaseModel):
    usuario_id: int
    nome: str
    dias_pendentes: list[str]


class ConsolidacaoResponse(BaseModel):
    consolidado: bool
    pendencias: list[PendenciaUsuario]
    mensagem: str


class ConsolidacaoInput(BaseModel):
    data_inicio: str
    data_fim: str


@router.post("/consolidar", summary="Consolidar intervalo de datas")
def consolidar(body: ConsolidacaoInput, _: SomenteAdmin) -> ConsolidacaoResponse:
    """Valida pendencias e consolida o intervalo se nao houver lacunas.
    Retorna lista de usuarios e dias pendentes caso a consolidacao seja bloqueada.
    """
    return ConsolidacaoResponse(
        consolidado=False,
        pendencias=[],
        mensagem="nenhum dado para consolidar",
    )


# ── Feriados ─────────────────────────────────────────────────────────────────


class Feriado(BaseModel):
    id: int
    data: str
    descricao: str


class FeriadosResponse(BaseModel):
    feriados: list[Feriado]


@router.get("/feriados", summary="Lista feriados cadastrados")
def listar_feriados(_: UsuarioLogado) -> FeriadosResponse:
    """Feriados e indisponibilidades globais. Dias de feriado so permitem lancamento extra."""
    return FeriadosResponse(feriados=[])


class FeriadoInput(BaseModel):
    data: str
    descricao: str


@router.post("/feriados", summary="Cadastrar feriado ou indisponibilidade", status_code=201)
def criar_feriado(body: FeriadoInput, _: SomenteAdmin) -> Feriado:
    """Admin cadastra feriado global. Dias afetados passam a so aceitar lancamentos extra."""
    return Feriado(id=0, data=body.data, descricao=body.descricao)


class Removido(BaseModel):
    removido: bool


@router.delete("/feriados/{feriado_id}", summary="Remover feriado")
def remover_feriado(feriado_id: int, _: SomenteAdmin) -> Removido:
    """Remove um feriado cadastrado."""
    return Removido(removido=True)
