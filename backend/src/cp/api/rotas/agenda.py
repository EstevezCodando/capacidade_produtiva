"""Rotas de agenda (apontamentos e planejamento).

Politica de autorizacao:
    GET    /agenda/minha                            — autenticado
    POST   /agenda/minha/apontamento               — autenticado
    PUT    /agenda/minha/apontamento/{id}           — autenticado
    DELETE /agenda/minha/apontamento/{id}           — autenticado
    GET    /agenda/usuarios/{id}                    — admin
    POST   /agenda/usuarios/{id}/apontamento        — admin
    GET    /agenda/planejamento                     — admin
    POST   /agenda/planejamento                     — admin
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from cp.api.deps import SomenteAdmin, UsuarioLogado

router = APIRouter(prefix="/agenda", tags=["agenda"])


# ── Modelos compartilhados ───────────────────────────────────────────────────


class Apontamento(BaseModel):
    id: int
    data: str
    bloco_id: int | None
    bloco_nome: str | None
    minutos: int
    tipo: Literal["normal", "extra"]


class DiaDaAgenda(BaseModel):
    data: str
    status: Literal["ABERTO", "CONSOLIDADO"]
    teto_normal_min: int
    teto_extra_min: int
    apontado_normal_min: int
    apontado_extra_min: int
    apontamentos: list[Apontamento]


class AgendaResponse(BaseModel):
    usuario_id: int
    dias: list[DiaDaAgenda]


# ── Minha agenda (operador) ──────────────────────────────────────────────────


@router.get("/minha", summary="Agenda do usuario autenticado")
def minha_agenda(
    usuario: UsuarioLogado,
    data_inicio: str = Query(..., description="ISO date YYYY-MM-DD"),
    data_fim: str = Query(..., description="ISO date YYYY-MM-DD"),
) -> AgendaResponse:
    """Apontamentos e planejamento do usuario autenticado no intervalo.
    Inclui status do dia (ABERTO/CONSOLIDADO), teto normal e extra.
    """
    return AgendaResponse(usuario_id=usuario.usuario_id, dias=[])


class ApontamentoInput(BaseModel):
    data: str
    bloco_id: int | None = None
    minutos: int
    tipo: Literal["normal", "extra"]


class ApontamentoCriado(BaseModel):
    id: int
    data: str
    minutos: int
    tipo: str
    alertas: list[str]


@router.post("/minha/apontamento", summary="Lancar apontamento proprio", status_code=201)
def criar_apontamento(
    body: ApontamentoInput,
    usuario: UsuarioLogado,
) -> ApontamentoCriado:
    """Registra apontamento do usuario autenticado.
    Dia futuro e bloqueado. Dia CONSOLIDADO rejeita normal; permite extra com alerta.
    """
    return ApontamentoCriado(id=0, data=body.data, minutos=body.minutos, tipo=body.tipo, alertas=[])


class ApontamentoEditado(BaseModel):
    id: int
    minutos: int
    alertas: list[str]


class ApontamentoEdicaoInput(BaseModel):
    minutos: int


@router.put("/minha/apontamento/{apontamento_id}", summary="Editar apontamento proprio")
def editar_apontamento(
    apontamento_id: int,
    body: ApontamentoEdicaoInput,
    _: UsuarioLogado,
) -> ApontamentoEditado:
    """Edita apontamento em dia ABERTO com log de auditoria. Dia CONSOLIDADO bloqueia normal."""
    return ApontamentoEditado(id=apontamento_id, minutos=body.minutos, alertas=[])


class Removido(BaseModel):
    removido: bool


@router.delete("/minha/apontamento/{apontamento_id}", summary="Remover apontamento proprio")
def remover_apontamento(apontamento_id: int, _: UsuarioLogado) -> Removido:
    """Remove apontamento em dia ABERTO."""
    return Removido(removido=True)


# ── Agenda de outro usuario (admin) ─────────────────────────────────────────


@router.get("/usuarios/{usuario_id}", summary="Agenda de um usuario (admin)")
def agenda_usuario(
    usuario_id: int,
    _: SomenteAdmin,
    data_inicio: str = Query(..., description="ISO date YYYY-MM-DD"),
    data_fim: str = Query(..., description="ISO date YYYY-MM-DD"),
) -> AgendaResponse:
    """Admin visualiza agenda completa de qualquer usuario."""
    return AgendaResponse(usuario_id=usuario_id, dias=[])


@router.post(
    "/usuarios/{usuario_id}/apontamento",
    summary="Lancar apontamento por um usuario (admin)",
    status_code=201,
)
def criar_apontamento_admin(
    usuario_id: int,
    body: ApontamentoInput,
    _: SomenteAdmin,
) -> ApontamentoCriado:
    """Admin lanca apontamento em nome de operador.
    Permite lancamento em datas passadas ja consolidadas com alerta de auditoria.
    """
    return ApontamentoCriado(id=0, data=body.data, minutos=body.minutos, tipo=body.tipo, alertas=[])


# ── Planejamento (admin) ─────────────────────────────────────────────────────


class DiasPlanejados(BaseModel):
    usuario_id: int
    dias: list[DiaDaAgenda]


class PlanejamentoGeral(BaseModel):
    operadores: list[DiasPlanejados]


@router.get("/planejamento", summary="Agenda planejada de todos os operadores (admin)")
def planejamento(
    _: SomenteAdmin,
    data_inicio: str = Query(..., description="ISO date YYYY-MM-DD"),
    data_fim: str = Query(..., description="ISO date YYYY-MM-DD"),
) -> PlanejamentoGeral:
    """Planejamento de todos os operadores no intervalo. Aba Gerenciar Agendas."""
    return PlanejamentoGeral(operadores=[])


class PlanejamentoInput(BaseModel):
    usuario_id: int
    data: str
    bloco_id: int | None = None
    minutos_planejados: int


class PlanejamentoCriado(BaseModel):
    id: int


@router.post("/planejamento", summary="Lancar ou atualizar planejamento (admin)", status_code=201)
def criar_planejamento(body: PlanejamentoInput, _: SomenteAdmin) -> PlanejamentoCriado:
    """Admin define agenda planejada de um operador para datas futuras."""
    return PlanejamentoCriado(id=0)
