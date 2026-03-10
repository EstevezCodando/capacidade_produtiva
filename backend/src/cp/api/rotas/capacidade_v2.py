"""Rotas de Capacidade (teto diário, status, consolidação, feriados).

Política de autorização:
    GET  /capacidade/config                     — admin
    PUT  /capacidade/config                     — admin
    POST /capacidade/parametro                  — admin
    PUT  /capacidade/parametro/{id}             — admin
    GET  /capacidade/status                     — admin
    POST /capacidade/consolidar-periodo         — admin
    GET  /capacidade/feriados                   — autenticado
    GET  /capacidade/meu-periodo                — autenticado (operador)
    GET  /capacidade/usuario/{usuario_id}       — admin
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from cp.api.deps import SomenteAdmin, UsuarioLogado
from cp.domain.capacidade.exceptions import (
    CapacidadeError,
    IntervaloInvalidoError,
    PermissaoError,
    RegistroNaoEncontradoError,
    ValidacaoError,
    VigenciaConflitanteError,
)
from cp.domain.capacidade.schemas import (
    CapacidadePeriodoResponse,
    ConfigTetoResponse,
    ConsolidacaoInput,
    ConsolidacaoResponse,
    FeriadosListResponse,
    ParametroCapacidadeInput,
    ParametroCapacidadeResponse,
    PendenciaResponse,
    ResumoCapacidadePeriodo,
    StatusDiasResponse,
)
from cp.services.capacidade import AgendaService, CapacidadeService, ConsolidacaoService

router = APIRouter(prefix="/capacidade", tags=["capacidade"])


def _get_capacidade_service(request: Request) -> CapacidadeService:
    """Obtém o serviço de capacidade a partir do estado da app."""
    engine = request.app.state.engine_cp
    return CapacidadeService(engine)


def _get_agenda_service(request: Request) -> AgendaService:
    """Obtém o serviço de agenda a partir do estado da app."""
    engine = request.app.state.engine_cp
    return AgendaService(engine)


def _get_consolidacao_service(request: Request) -> ConsolidacaoService:
    """Obtém o serviço de consolidação a partir do estado da app."""
    engine = request.app.state.engine_cp
    return ConsolidacaoService(engine)


def _handle_exception(exc: Exception) -> None:
    """Converte exceções de domínio em HTTPException."""
    if isinstance(exc, VigenciaConflitanteError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, IntervaloInvalidoError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, RegistroNaoEncontradoError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    if isinstance(exc, ValidacaoError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, PermissaoError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    if isinstance(exc, CapacidadeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    raise exc


# ──────────────────────────────────────────────────────────────────────────────
# Configuração de Teto (compatibilidade)
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/config", summary="Configuração do teto diário vigente")
def config_teto(request: Request, _: SomenteAdmin) -> ConfigTetoResponse:
    """Retorna teto normal e extra vigentes."""
    service = _get_capacidade_service(request)

    parametro = service.obter_parametro_vigente(date.today())

    if not parametro:
        return ConfigTetoResponse(
            teto_normal_min=360,
            teto_extra_min=240,
            vigencia_inicio=date(2026, 1, 1),
            vigencia_fim=None,
            configurado_em=None,
            configurado_por=None,
        )

    return ConfigTetoResponse(
        teto_normal_min=parametro.minutos_dia_util_default,
        teto_extra_min=parametro.minutos_extra_maximo_default,
        vigencia_inicio=parametro.data_inicio_vigencia,
        vigencia_fim=parametro.data_fim_vigencia,
        configurado_em=parametro.criado_em,
        configurado_por=parametro.criado_por,
    )


class ConfigTetoInput(BaseModel):
    """Entrada para atualização rápida do teto."""

    teto_normal_min: int = Field(..., gt=0)
    teto_extra_min: int = Field(..., ge=0)


@router.put("/config", summary="Atualizar teto diário vigente")
def atualizar_config_teto(
    request: Request,
    body: ConfigTetoInput,
    admin: SomenteAdmin,
) -> ConfigTetoResponse:
    """Atualiza o teto normal e extra do parâmetro vigente."""
    service = _get_capacidade_service(request)

    try:
        parametro = service.obter_parametro_vigente(date.today())

        if not parametro:
            # Criar novo parâmetro
            parametro = service.criar_parametro(
                minutos_dia_util=body.teto_normal_min,
                minutos_extra_max=body.teto_extra_min,
                data_inicio=date.today(),
                data_fim=None,
                criado_por=admin.usuario_id,
            )
        else:
            # Atualizar existente
            parametro = service.atualizar_parametro(
                id=parametro.id,
                minutos_dia_util=body.teto_normal_min,
                minutos_extra_max=body.teto_extra_min,
                data_fim=None,
                atualizado_por=admin.usuario_id,
            )

        return ConfigTetoResponse(
            teto_normal_min=parametro.minutos_dia_util_default,
            teto_extra_min=parametro.minutos_extra_maximo_default,
            vigencia_inicio=parametro.data_inicio_vigencia,
            vigencia_fim=parametro.data_fim_vigencia,
            configurado_em=parametro.criado_em,
            configurado_por=parametro.criado_por,
        )
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Parâmetros de Capacidade (novo)
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/parametro", summary="Criar parâmetro de capacidade (admin)", status_code=201)
def criar_parametro(
    request: Request,
    body: ParametroCapacidadeInput,
    admin: SomenteAdmin,
) -> ParametroCapacidadeResponse:
    """Admin cria novo parâmetro de capacidade com vigência."""
    service = _get_capacidade_service(request)

    try:
        parametro = service.criar_parametro(
            minutos_dia_util=body.minutos_dia_util_default,
            minutos_extra_max=body.minutos_extra_maximo_default,
            data_inicio=body.data_inicio_vigencia,
            data_fim=body.data_fim_vigencia,
            criado_por=admin.usuario_id,
        )

        return ParametroCapacidadeResponse(
            id=parametro.id,
            minutos_dia_util_default=parametro.minutos_dia_util_default,
            minutos_extra_maximo_default=parametro.minutos_extra_maximo_default,
            data_inicio_vigencia=parametro.data_inicio_vigencia,
            data_fim_vigencia=parametro.data_fim_vigencia,
            criado_por=parametro.criado_por,
            criado_em=parametro.criado_em,
        )
    except Exception as exc:
        _handle_exception(exc)


class ParametroCapacidadeUpdateInput(BaseModel):
    """Entrada para atualização de parâmetro."""

    minutos_dia_util_default: int | None = Field(None, gt=0)
    minutos_extra_maximo_default: int | None = Field(None, ge=0)
    data_fim_vigencia: date | None = None


@router.put("/parametro/{parametro_id}", summary="Atualizar parâmetro de capacidade (admin)")
def atualizar_parametro(
    request: Request,
    parametro_id: int,
    body: ParametroCapacidadeUpdateInput,
    admin: SomenteAdmin,
) -> ParametroCapacidadeResponse:
    """Admin atualiza parâmetro de capacidade existente."""
    service = _get_capacidade_service(request)

    try:
        parametro = service.atualizar_parametro(
            id=parametro_id,
            minutos_dia_util=body.minutos_dia_util_default,
            minutos_extra_max=body.minutos_extra_maximo_default,
            data_fim=body.data_fim_vigencia,
            atualizado_por=admin.usuario_id,
        )

        return ParametroCapacidadeResponse(
            id=parametro.id,
            minutos_dia_util_default=parametro.minutos_dia_util_default,
            minutos_extra_maximo_default=parametro.minutos_extra_maximo_default,
            data_inicio_vigencia=parametro.data_inicio_vigencia,
            data_fim_vigencia=parametro.data_fim_vigencia,
            criado_por=parametro.criado_por,
            criado_em=parametro.criado_em,
        )
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Status dos Dias
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/status", summary="Status dos dias no intervalo")
def status_dias(
    request: Request,
    _: SomenteAdmin,
    data_inicio: date = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data de fim (YYYY-MM-DD)"),
) -> StatusDiasResponse:
    """Status (ABERTO/CONSOLIDADO) de cada dia do intervalo."""
    service = _get_consolidacao_service(request)

    dias = service.obter_status_dias(data_inicio, data_fim)
    return StatusDiasResponse(dias=dias)


# ──────────────────────────────────────────────────────────────────────────────
# Consolidação
# ──────────────────────────────────────────────────────────────────────────────


class ConsolidacaoInputExtended(ConsolidacaoInput):
    """Entrada estendida para consolidação."""

    usuarios_ids: list[int] | None = Field(
        None,
        description="IDs dos usuários a consolidar. Se vazio, consolida todos.",
    )
    ignorar_pendencias: bool = Field(
        False,
        description="Se True, consolida mesmo com pendências (requer admin).",
    )


@router.post("/consolidar-periodo", summary="Consolidar intervalo de datas (admin)")
def consolidar_periodo(
    request: Request,
    body: ConsolidacaoInputExtended,
    admin: SomenteAdmin,
) -> ConsolidacaoResponse:
    """Valida pendências e consolida o intervalo.

    Retorna lista de usuários e dias pendentes caso a consolidação seja bloqueada.
    """
    service = _get_consolidacao_service(request)

    try:
        if body.usuarios_ids:
            resultado = service.consolidar_periodo_todos_usuarios(
                usuarios_ids=body.usuarios_ids,
                data_inicio=body.data_inicio,
                data_fim=body.data_fim,
                executor_id=admin.usuario_id,
                ignorar_pendencias=body.ignorar_pendencias,
            )
        else:
            # Se não especificou usuários, precisa buscar todos os usuários ativos
            # Por ora, retorna erro indicando que precisa especificar
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Especifique os IDs dos usuários a consolidar em usuarios_ids",
            )

        pendencias_response = [
            PendenciaResponse(
                usuario_id=p.usuario_id,
                data=p.data,
                tipo=p.tipo,
                motivo=p.motivo,
            )
            for p in resultado.pendencias
        ]

        return ConsolidacaoResponse(
            consolidado=resultado.consolidado,
            pendencias=pendencias_response,
            mensagem=resultado.mensagem,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Feriados (listagem)
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/feriados", summary="Lista feriados cadastrados")
def listar_feriados(request: Request, _: UsuarioLogado) -> FeriadosListResponse:
    """Lista todos os feriados cadastrados."""
    service = _get_agenda_service(request)

    from cp.domain.capacidade.schemas import FeriadoResponse

    feriados = service.listar_feriados()

    return FeriadosListResponse(
        feriados=[
            FeriadoResponse(
                id=f.id,
                data=f.data,
                descricao=f.descricao,
                criado_por=f.criado_por,
                criado_em=f.criado_em,
            )
            for f in feriados
        ]
    )


# ──────────────────────────────────────────────────────────────────────────────
# Consultas Analíticas - Operador
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/meu-periodo", summary="Capacidade do usuário autenticado no período")
def meu_periodo(
    request: Request,
    usuario: UsuarioLogado,
    data_inicio: date = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data de fim (YYYY-MM-DD)"),
    bloco_id: int | None = Query(None, description="Filtrar por bloco"),
) -> CapacidadePeriodoResponse:
    """Retorna resumo analítico de capacidade do usuário no período."""
    service = _get_capacidade_service(request)
    agenda_service = _get_agenda_service(request)

    try:
        resumo = service.calcular_resumo_periodo(
            usuario_id=usuario.usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            bloco_id=bloco_id,
        )

        detalhes = agenda_service.obter_agenda_completa(
            usuario.usuario_id, data_inicio, data_fim
        )

        return CapacidadePeriodoResponse(
            resumo=resumo,
            detalhes_por_dia=detalhes,
        )
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Consultas Analíticas - Admin
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/usuario/{usuario_id}", summary="Capacidade de um usuário (admin)")
def capacidade_usuario(
    request: Request,
    usuario_id: int,
    _: SomenteAdmin,
    data_inicio: date = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data de fim (YYYY-MM-DD)"),
    bloco_id: int | None = Query(None, description="Filtrar por bloco"),
) -> CapacidadePeriodoResponse:
    """Admin consulta resumo analítico de capacidade de qualquer usuário."""
    service = _get_capacidade_service(request)
    agenda_service = _get_agenda_service(request)

    try:
        resumo = service.calcular_resumo_periodo(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            bloco_id=bloco_id,
        )

        detalhes = agenda_service.obter_agenda_completa(
            usuario_id, data_inicio, data_fim
        )

        return CapacidadePeriodoResponse(
            resumo=resumo,
            detalhes_por_dia=detalhes,
        )
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Materialização de Capacidade
# ──────────────────────────────────────────────────────────────────────────────


class MaterializarInput(BaseModel):
    """Entrada para materialização de capacidade."""

    usuario_id: int
    data_inicio: date
    data_fim: date


@router.post("/materializar", summary="Materializar capacidade diária (admin)", status_code=201)
def materializar_capacidade(
    request: Request,
    body: MaterializarInput,
    admin: SomenteAdmin,
) -> dict[str, int]:
    """Admin materializa capacidade diária para um usuário no período.

    Útil para pré-popular a tabela capacidade_dia antes do uso.
    """
    service = _get_capacidade_service(request)

    try:
        capacidades = service.materializar_periodo(
            usuario_id=body.usuario_id,
            data_inicio=body.data_inicio,
            data_fim=body.data_fim,
            executor_id=admin.usuario_id,
        )

        return {"dias_materializados": len(capacidades)}
    except Exception as exc:
        _handle_exception(exc)
