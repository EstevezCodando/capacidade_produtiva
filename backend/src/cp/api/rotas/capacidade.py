"""Rotas de Capacidade (teto diário, tipos de atividade, consolidação e feriados).

Política de autorização:
    GET    /capacidade/tipos-atividade             — admin
    PUT    /capacidade/tipos-atividade/{id}/cor    — admin
    GET    /capacidade/config                      — admin
    PUT    /capacidade/config                      — admin
    POST   /capacidade/parametro                   — admin
    PUT    /capacidade/parametro/{id}              — admin
    GET    /capacidade/status                      — admin
    POST   /capacidade/consolidar-periodo          — admin
    POST   /capacidade/desconsolidar-periodo       — admin
    GET    /capacidade/exportar-sem-lancamento     — admin
    GET    /capacidade/feriados                    — autenticado
    POST   /capacidade/feriados                    — admin
    DELETE /capacidade/feriados/{id}               — admin
    GET    /capacidade/meu-periodo                 — autenticado
    GET    /capacidade/usuario/{usuario_id}        — admin
    POST   /capacidade/materializar                — admin
"""

from __future__ import annotations

from datetime import date

import csv
import io

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from cp.api.deps import SomenteAdmin, UsuarioLogado
from cp.api.exception_handlers import handle_domain_exception
from cp.domain.capacidade.constants import MINUTOS_DIA_UTIL_DEFAULT, MINUTOS_EXTRA_MAXIMO_DEFAULT
from cp.domain.capacidade.models import TipoAtividade
from cp.domain.capacidade.schemas import (
    CapacidadePeriodoResponse,
    ConfigTetoResponse,
    ConsolidacaoInput,
    ConsolidacaoResponse,
    DesconsolidacaoResponse,
    ExportacaoInconsistenciasResponse,
    FeriadoInput,
    FeriadoResponse,
    FeriadosListResponse,
    ParametroCapacidadeInput,
    ParametroCapacidadeResponse,
    PendenciaResponse,
    RemovidoResponse,
    StatusDiasResponse,
)
from cp.services.capacidade import AgendaService, CapacidadeService, ConsolidacaoService

router = APIRouter(prefix="/capacidade", tags=["capacidade"])


class TipoAtividadeConfigResponse(BaseModel):
    id: int
    codigo: str
    nome: str
    grupo: str
    bloco_id: int | None
    cor: str


class TipoAtividadeCorInput(BaseModel):
    cor: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")



class ConfigTetoInput(BaseModel):
    """Entrada para atualização rápida do teto."""

    teto_normal_min: int = Field(..., gt=0)
    teto_extra_min: int = Field(..., ge=0)


class ParametroCapacidadeUpdateInput(BaseModel):
    """Entrada para atualização de parâmetro."""

    minutos_dia_util_default: int | None = Field(None, gt=0)
    minutos_extra_maximo_default: int | None = Field(None, ge=0)
    data_fim_vigencia: date | None = None


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


class MaterializarInput(BaseModel):
    """Entrada para materialização de capacidade."""

    usuario_id: int
    data_inicio: date
    data_fim: date


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



def _mapear_tipo_atividade(tipo: TipoAtividade) -> TipoAtividadeConfigResponse:
    return TipoAtividadeConfigResponse(
        id=tipo.id,
        codigo=tipo.codigo.value,
        nome=tipo.nome,
        grupo=tipo.grupo.value,
        bloco_id=tipo.bloco_id,
        cor=tipo.cor,
    )


@router.get("/tipos-atividade", summary="Lista atividades configuráveis")
def listar_tipos_atividade_config(request: Request, _: SomenteAdmin) -> list[TipoAtividadeConfigResponse]:
    service = _get_agenda_service(request)
    tipos = service._tipo_atividade_repo.listar_configuraveis()
    return [_mapear_tipo_atividade(tipo) for tipo in tipos]


@router.put("/tipos-atividade/{tipo_atividade_id}/cor", summary="Atualiza a cor de uma atividade")
def atualizar_cor_tipo_atividade(
    request: Request,
    tipo_atividade_id: int,
    body: TipoAtividadeCorInput,
    _: SomenteAdmin,
) -> TipoAtividadeConfigResponse:
    service = _get_agenda_service(request)
    tipo = service._tipo_atividade_repo.atualizar_cor(tipo_atividade_id, body.cor.upper())
    if not tipo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de atividade não encontrado.")
    return _mapear_tipo_atividade(tipo)


@router.get("/config", summary="Configuração do teto diário vigente")
def config_teto(request: Request, _: SomenteAdmin) -> ConfigTetoResponse:
    """Retorna teto normal e extra vigentes."""
    service = _get_capacidade_service(request)
    parametro = service.obter_parametro_vigente(date.today())

    if not parametro:
        return ConfigTetoResponse(
            teto_normal_min=MINUTOS_DIA_UTIL_DEFAULT,
            teto_extra_min=MINUTOS_EXTRA_MAXIMO_DEFAULT,
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
            parametro = service.criar_parametro(
                minutos_dia_util=body.teto_normal_min,
                minutos_extra_max=body.teto_extra_min,
                data_inicio=date.today(),
                data_fim=None,
                criado_por=admin.usuario_id,
            )
        else:
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
        handle_domain_exception(exc)


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
        handle_domain_exception(exc)


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
        handle_domain_exception(exc)


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


@router.post("/consolidar-periodo", summary="Consolidar intervalo de datas (admin)")
def consolidar_periodo(
    request: Request,
    body: ConsolidacaoInputExtended,
    admin: SomenteAdmin,
) -> ConsolidacaoResponse:
    """Valida pendências e consolida o intervalo."""
    service = _get_consolidacao_service(request)

    try:
        if not body.usuarios_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Especifique os IDs dos usuários a consolidar em usuarios_ids",
            )

        resultado = service.consolidar_periodo_todos_usuarios(
            usuarios_ids=body.usuarios_ids,
            data_inicio=body.data_inicio,
            data_fim=body.data_fim,
            executor_id=admin.usuario_id,
            ignorar_pendencias=body.ignorar_pendencias,
        )
        pendencias_response = [
            PendenciaResponse(
                usuario_id=p.usuario_id,
                data=p.data,
                tipo=p.tipo,
                motivo=p.motivo,
                minutos_nao_lancados=p.minutos_nao_lancados,
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
        handle_domain_exception(exc)


@router.post("/desconsolidar-periodo", summary="Desconsolidar intervalo de datas (admin)")
def desconsolidar_periodo(
    request: Request,
    body: ConsolidacaoInputExtended,
    admin: SomenteAdmin,
) -> DesconsolidacaoResponse:
    """Reabre período consolidado, permitindo edição pelos operadores novamente."""
    service = _get_consolidacao_service(request)

    try:
        if not body.usuarios_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Especifique os IDs dos usuários em usuarios_ids",
            )

        resultado = service.desconsolidar_periodo_todos_usuarios(
            usuarios_ids=body.usuarios_ids,
            data_inicio=body.data_inicio,
            data_fim=body.data_fim,
            executor_id=admin.usuario_id,
        )
        return resultado
    except HTTPException:
        raise
    except Exception as exc:
        handle_domain_exception(exc)


@router.get("/exportar-sem-lancamento", summary="Exportar inconsistências de lançamentos como CSV")
def exportar_sem_lancamento(
    request: Request,
    _: SomenteAdmin,
    data_inicio: date = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data de fim (YYYY-MM-DD)"),
    usuarios_ids: str = Query(..., description="IDs dos usuários separados por vírgula"),
) -> StreamingResponse:
    """Gera CSV com usuário, data e horas não lançadas para o período especificado.

    O CSV inclui apenas dias úteis com ausência ou incompletude de lançamentos.
    """
    service = _get_consolidacao_service(request)

    try:
        ids_list = [int(i.strip()) for i in usuarios_ids.split(",") if i.strip()]
        if not ids_list:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Informe ao menos um ID de usuário em usuarios_ids",
            )

        resultado = service.obter_inconsistencias(ids_list, data_inicio, data_fim)

        # Gera CSV em memória
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["Nome do Usuário", "Data", "Horas Não Lançadas"])
        for linha in resultado.linhas:
            writer.writerow([
                linha.nome_usuario,
                linha.data.strftime("%d/%m/%Y"),
                f"{linha.horas_nao_lancadas:.1f}".replace(".", ","),
            ])

        output.seek(0)
        nome_arquivo = f"inconsistencias_{data_inicio}_{data_fim}.csv"

        return StreamingResponse(
            iter([output.getvalue().encode("utf-8-sig")]),  # utf-8-sig para compatibilidade Excel
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        handle_domain_exception(exc)


@router.get("/feriados", summary="Lista feriados cadastrados")
def listar_feriados(request: Request, _: UsuarioLogado) -> FeriadosListResponse:
    """Lista todos os feriados cadastrados."""
    service = _get_agenda_service(request)
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


@router.post("/feriados", summary="Cadastrar feriado ou indisponibilidade", status_code=201)
def criar_feriado(request: Request, body: FeriadoInput, admin: SomenteAdmin) -> dict[str, object]:
    """Admin cadastra feriado global."""
    service = _get_agenda_service(request)
    try:
        feriado = service.criar_feriado(body.data, body.descricao, admin.usuario_id)
        return {
            "id": feriado.id,
            "data": feriado.data,
            "descricao": feriado.descricao,
            "criado_por": feriado.criado_por,
            "criado_em": feriado.criado_em,
        }
    except Exception as exc:
        handle_domain_exception(exc)


@router.delete("/feriados/{feriado_id}", summary="Remover feriado")
def remover_feriado(request: Request, feriado_id: int, admin: SomenteAdmin) -> RemovidoResponse:
    """Remove um feriado cadastrado."""
    service = _get_agenda_service(request)
    try:
        removido = service.remover_feriado(feriado_id, admin.usuario_id)
        return RemovidoResponse(removido=removido)
    except Exception as exc:
        handle_domain_exception(exc)


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
        detalhes = agenda_service.obter_agenda_completa(usuario.usuario_id, data_inicio, data_fim)
        return CapacidadePeriodoResponse(resumo=resumo, detalhes_por_dia=detalhes)
    except Exception as exc:
        handle_domain_exception(exc)


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
        detalhes = agenda_service.obter_agenda_completa(usuario_id, data_inicio, data_fim)
        return CapacidadePeriodoResponse(resumo=resumo, detalhes_por_dia=detalhes)
    except Exception as exc:
        handle_domain_exception(exc)


@router.post("/materializar", summary="Materializar capacidade diária (admin)", status_code=201)
def materializar_capacidade(
    request: Request,
    body: MaterializarInput,
    admin: SomenteAdmin,
) -> dict[str, int]:
    """Admin materializa capacidade diária para um usuário no período."""
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
        handle_domain_exception(exc)
