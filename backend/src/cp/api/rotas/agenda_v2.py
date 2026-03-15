"""Rotas de Agenda (apontamentos e planejamento).

Política de autorização:
    GET    /agenda/meu-planejamento              — autenticado (operador)
    GET    /agenda/meus-lancamentos              — autenticado (operador)
    POST   /agenda/lancamento                    — autenticado (operador)
    PUT    /agenda/lancamento/{id}               — autenticado (operador)
    DELETE /agenda/lancamento/{id}               — autenticado (operador)
    GET    /agenda/usuario/{usuario_id}          — admin
    POST   /agenda/planejamento                  — admin
    PUT    /agenda/planejamento/{id}             — admin
    DELETE /agenda/planejamento/{id}             — admin
    POST   /agenda/lancamento-admin              — admin
    PUT    /agenda/lancamento-admin/{id}         — admin
    DELETE /agenda/lancamento-admin/{id}         — admin
    POST   /agenda/feriado                       — admin
    DELETE /agenda/feriado/{id}                  — admin
    POST   /agenda/indisponibilidade             — admin
    DELETE /agenda/indisponibilidade/{id}        — admin
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request, status

from cp.api.deps import SomenteAdmin, UsuarioLogado
from cp.domain.capacidade.exceptions import (
    AcessoNegadoError,
    CapacidadeError,
    DataFuturaError,
    DiaConsolidadoError,
    DiaIndisponivelError,
    FeriadoDuplicadoError,
    IndisponibilidadeSobrepostaError,
    IntervaloInvalidoError,
    LimiteCapacidadeExcedidoError,
    PermissaoError,
    RegistroNaoEncontradoError,
    ValidacaoError,
)
from cp.domain.capacidade.schemas import (
    AgendaCompletaResponse,
    FeriadoInput,
    FeriadoResponse,
    IndisponibilidadeInput,
    IndisponibilidadeResponse,
    LancamentoAdminInput,
    LancamentoInput,
    LancamentoResponse,
    LancamentoUpdateInput,
    PlanejamentoInput,
    PlanejamentoLoteInput,
    PlanejamentoRemocaoLoteInput,
    PlanejamentoResponse,
    PlanejamentoUpdateInput,
    RemovidoResponse,
)
from cp.services.capacidade import AgendaService

router = APIRouter(prefix="/agenda", tags=["agenda"])


def _get_agenda_service(request: Request) -> AgendaService:
    """Obtém o serviço de agenda a partir do estado da app."""
    engine = request.app.state.engine_cp
    return AgendaService(engine)


def _handle_exception(exc: Exception) -> None:
    """Converte exceções de domínio em HTTPException."""
    if isinstance(exc, DataFuturaError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    if isinstance(exc, DiaConsolidadoError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    if isinstance(exc, AcessoNegadoError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    if isinstance(exc, LimiteCapacidadeExcedidoError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, DiaIndisponivelError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, IntervaloInvalidoError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, FeriadoDuplicadoError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, IndisponibilidadeSobrepostaError):
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
# Rotas do Operador - Planejamento
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/meu-planejamento", summary="Planejamento do usuário autenticado")
def meu_planejamento(
    request: Request,
    usuario: UsuarioLogado,
    data_inicio: date = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data de fim (YYYY-MM-DD)"),
) -> AgendaCompletaResponse:
    """Retorna a agenda completa do usuário autenticado no período.

    Inclui:
    - Status de cada dia (ABERTO/CONSOLIDADO)
    - Teto de minutos normais e extras
    - Minutos já apontados
    - Planejamentos e lançamentos
    """
    service = _get_agenda_service(request)

    try:
        dias = service.obter_agenda_completa(usuario.usuario_id, data_inicio, data_fim)
        return AgendaCompletaResponse(
            usuario_id=usuario.usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            dias=dias,
        )
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Rotas do Operador - Lançamentos
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/meus-lancamentos", summary="Lançamentos do usuário autenticado")
def meus_lancamentos(
    request: Request,
    usuario: UsuarioLogado,
    data_inicio: date = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data de fim (YYYY-MM-DD)"),
) -> list[LancamentoResponse]:
    """Retorna os lançamentos do usuário autenticado no período."""
    service = _get_agenda_service(request)

    lancamentos = service.listar_lancamentos_usuario(
        usuario.usuario_id, data_inicio, data_fim
    )

    return [
        LancamentoResponse(
            id=l.id,
            usuario_id=l.usuario_id,
            data_lancamento=l.data_lancamento,
            bloco_id=l.bloco_id,
            tipo_atividade_id=l.tipo_atividade_id,
            tipo_atividade_codigo=l.tipo_atividade.codigo,
            tipo_atividade_nome=l.tipo_atividade.nome,
            tipo_atividade_cor=l.tipo_atividade.cor,
            faixa_minuto=l.faixa_minuto,
            minutos=l.minutos,
            descricao=l.descricao,
            criado_por=l.criado_por,
            atualizado_por=l.atualizado_por,
            criado_em=l.criado_em,
            atualizado_em=l.atualizado_em,
        )
        for l in lancamentos
    ]


@router.post("/lancamento", summary="Criar lançamento próprio", status_code=201)
def criar_lancamento(
    request: Request,
    body: LancamentoInput,
    usuario: UsuarioLogado,
) -> LancamentoResponse:
    """Registra lançamento do usuário autenticado.

    Regras:
    - Não permite lançamento em data futura
    - Valida capacidade normal do dia
    - Dia consolidado só permite hora extra
    """
    service = _get_agenda_service(request)

    try:
        lancamento, alertas = service.criar_lancamento(
            usuario_id=usuario.usuario_id,
            data=body.data,
            bloco_id=body.bloco_id,
            tipo_atividade=body.tipo_atividade,
            faixa=body.faixa,
            minutos=body.minutos,
            descricao=body.descricao,
            criado_por=usuario.usuario_id,
            eh_admin=False,
            data_atual=date.today(),
        )

        return LancamentoResponse(
            id=lancamento.id,
            usuario_id=lancamento.usuario_id,
            data_lancamento=lancamento.data_lancamento,
            bloco_id=lancamento.bloco_id,
            tipo_atividade_id=lancamento.tipo_atividade_id,
            tipo_atividade_codigo=lancamento.tipo_atividade.codigo,
            tipo_atividade_nome=lancamento.tipo_atividade.nome,
            tipo_atividade_cor=lancamento.tipo_atividade.cor,
            faixa_minuto=lancamento.faixa_minuto,
            minutos=lancamento.minutos,
            descricao=lancamento.descricao,
            criado_por=lancamento.criado_por,
            atualizado_por=lancamento.atualizado_por,
            criado_em=lancamento.criado_em,
            atualizado_em=lancamento.atualizado_em,
            alertas=alertas,
        )
    except Exception as exc:
        _handle_exception(exc)


@router.put("/lancamento/{lancamento_id}", summary="Editar lançamento próprio")
def editar_lancamento(
    request: Request,
    lancamento_id: int,
    body: LancamentoUpdateInput,
    usuario: UsuarioLogado,
) -> LancamentoResponse:
    """Edita lançamento do usuário autenticado.

    Regras:
    - Só pode editar lançamentos próprios
    - Dia consolidado só permite editar hora extra
    """
    service = _get_agenda_service(request)

    try:
        lancamento, alertas = service.atualizar_lancamento(
            id=lancamento_id,
            minutos=body.minutos,
            descricao=body.descricao,
            atualizado_por=usuario.usuario_id,
            eh_admin=False,
        )

        return LancamentoResponse(
            id=lancamento.id,
            usuario_id=lancamento.usuario_id,
            data_lancamento=lancamento.data_lancamento,
            bloco_id=lancamento.bloco_id,
            tipo_atividade_id=lancamento.tipo_atividade_id,
            tipo_atividade_codigo=lancamento.tipo_atividade.codigo,
            tipo_atividade_nome=lancamento.tipo_atividade.nome,
            tipo_atividade_cor=lancamento.tipo_atividade.cor,
            faixa_minuto=lancamento.faixa_minuto,
            minutos=lancamento.minutos,
            descricao=lancamento.descricao,
            criado_por=lancamento.criado_por,
            atualizado_por=lancamento.atualizado_por,
            criado_em=lancamento.criado_em,
            atualizado_em=lancamento.atualizado_em,
            alertas=alertas,
        )
    except Exception as exc:
        _handle_exception(exc)


@router.delete("/lancamento/{lancamento_id}", summary="Remover lançamento próprio")
def remover_lancamento(
    request: Request,
    lancamento_id: int,
    usuario: UsuarioLogado,
) -> RemovidoResponse:
    """Remove lançamento do usuário autenticado.

    Regras:
    - Só pode remover lançamentos próprios
    - Não permite remover em dia consolidado (exceto hora extra)
    """
    service = _get_agenda_service(request)

    try:
        removido = service.remover_lancamento(
            id=lancamento_id,
            removido_por=usuario.usuario_id,
            eh_admin=False,
        )
        return RemovidoResponse(removido=removido)
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Rotas do Admin - Visualização
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/usuario/{usuario_id}", summary="Agenda de um usuário (admin)")
def agenda_usuario(
    request: Request,
    usuario_id: int,
    _: SomenteAdmin,
    data_inicio: date = Query(..., description="Data de início (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data de fim (YYYY-MM-DD)"),
) -> AgendaCompletaResponse:
    """Admin visualiza agenda completa de qualquer usuário."""
    service = _get_agenda_service(request)

    try:
        dias = service.obter_agenda_completa(usuario_id, data_inicio, data_fim)
        return AgendaCompletaResponse(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            dias=dias,
        )
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Rotas do Admin - Planejamento
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/planejamento", summary="Criar planejamento (admin)", status_code=201)
def criar_planejamento(
    request: Request,
    body: PlanejamentoInput,
    admin: SomenteAdmin,
) -> PlanejamentoResponse:
    """Admin define planejamento de agenda para um usuário."""
    service = _get_agenda_service(request)

    try:
        planejamento = service.criar_planejamento(
            usuario_id=body.usuario_id,
            data=body.data,
            bloco_id=body.bloco_id,
            minutos_normais=body.minutos_planejados_normais,
            minutos_extras=body.minutos_planejados_extras,
            descricao=body.descricao,
            criado_por=admin.usuario_id,
        )

        return PlanejamentoResponse(
            id=planejamento.id,
            usuario_id=planejamento.usuario_id,
            data=planejamento.data,
            bloco_id=planejamento.bloco_id,
            minutos_planejados_normais=planejamento.minutos_planejados_normais,
            minutos_planejados_extras=planejamento.minutos_planejados_extras,
            descricao=planejamento.descricao,
            criado_por=planejamento.criado_por,
            criado_em=planejamento.criado_em,
            atualizado_em=planejamento.atualizado_em,
        )
    except Exception as exc:
        _handle_exception(exc)


@router.post("/planejamento/lote", summary="Criar planejamento em lote (admin)", status_code=201)
def criar_planejamento_lote(
    request: Request,
    body: PlanejamentoLoteInput,
    admin: SomenteAdmin,
) -> list[PlanejamentoResponse]:
    """Admin cria o mesmo planejamento para múltiplos usuários e datas."""
    service = _get_agenda_service(request)

    try:
        planejamentos = service.criar_planejamento_em_lote(
            usuario_ids=body.usuario_ids,
            datas=body.datas,
            bloco_id=body.bloco_id,
            minutos_normais=body.minutos_planejados_normais,
            minutos_extras=body.minutos_planejados_extras,
            descricao=body.descricao,
            criado_por=admin.usuario_id,
        )
        return [
            PlanejamentoResponse(
                id=planejamento.id,
                usuario_id=planejamento.usuario_id,
                data=planejamento.data,
                bloco_id=planejamento.bloco_id,
                minutos_planejados_normais=planejamento.minutos_planejados_normais,
                minutos_planejados_extras=planejamento.minutos_planejados_extras,
                descricao=planejamento.descricao,
                criado_por=planejamento.criado_por,
                criado_em=planejamento.criado_em,
                atualizado_em=planejamento.atualizado_em,
            )
            for planejamento in planejamentos
        ]
    except Exception as exc:
        _handle_exception(exc)


@router.post("/planejamento/remover-lote", summary="Remover planejamentos em lote (admin)")
def remover_planejamento_lote(
    request: Request,
    body: PlanejamentoRemocaoLoteInput,
    admin: SomenteAdmin,
) -> RemovidoResponse:
    """Admin inativa todos os planejamentos ativos para os usuários e datas selecionados."""
    service = _get_agenda_service(request)

    try:
        quantidade = service.remover_planejamento_em_lote(
            usuario_ids=body.usuario_ids,
            datas=body.datas,
            removido_por=admin.usuario_id,
        )
        return RemovidoResponse(removido=quantidade > 0, mensagem=f"{quantidade} planejamento(s) removido(s).")
    except Exception as exc:
        _handle_exception(exc)


@router.put("/planejamento/{planejamento_id}", summary="Atualizar planejamento (admin)")
def atualizar_planejamento(
    request: Request,
    planejamento_id: int,
    body: PlanejamentoUpdateInput,
    admin: SomenteAdmin,
) -> PlanejamentoResponse:
    """Admin atualiza planejamento existente."""
    service = _get_agenda_service(request)

    try:
        planejamento = service.atualizar_planejamento(
            id=planejamento_id,
            minutos_normais=body.minutos_planejados_normais,
            minutos_extras=body.minutos_planejados_extras,
            descricao=body.descricao,
            atualizado_por=admin.usuario_id,
        )

        return PlanejamentoResponse(
            id=planejamento.id,
            usuario_id=planejamento.usuario_id,
            data=planejamento.data,
            bloco_id=planejamento.bloco_id,
            minutos_planejados_normais=planejamento.minutos_planejados_normais,
            minutos_planejados_extras=planejamento.minutos_planejados_extras,
            descricao=planejamento.descricao,
            criado_por=planejamento.criado_por,
            criado_em=planejamento.criado_em,
            atualizado_em=planejamento.atualizado_em,
        )
    except Exception as exc:
        _handle_exception(exc)


@router.delete("/planejamento/{planejamento_id}", summary="Remover planejamento (admin)")
def remover_planejamento(
    request: Request,
    planejamento_id: int,
    admin: SomenteAdmin,
) -> RemovidoResponse:
    """Admin remove planejamento."""
    service = _get_agenda_service(request)

    try:
        removido = service.remover_planejamento(
            id=planejamento_id,
            removido_por=admin.usuario_id,
        )
        return RemovidoResponse(removido=removido)
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Rotas do Admin - Lançamentos
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/lancamento-admin", summary="Criar lançamento para usuário (admin)", status_code=201)
def criar_lancamento_admin(
    request: Request,
    body: LancamentoAdminInput,
    admin: SomenteAdmin,
) -> LancamentoResponse:
    """Admin registra lançamento em nome de um usuário.

    Permite lançamento em datas passadas já consolidadas com auditoria.
    """
    service = _get_agenda_service(request)

    try:
        lancamento, alertas = service.criar_lancamento(
            usuario_id=body.usuario_id,
            data=body.data,
            bloco_id=body.bloco_id,
            tipo_atividade=body.tipo_atividade,
            faixa=body.faixa,
            minutos=body.minutos,
            descricao=body.descricao,
            criado_por=admin.usuario_id,
            eh_admin=True,
            data_atual=date.today(),
        )

        return LancamentoResponse(
            id=lancamento.id,
            usuario_id=lancamento.usuario_id,
            data_lancamento=lancamento.data_lancamento,
            bloco_id=lancamento.bloco_id,
            tipo_atividade_id=lancamento.tipo_atividade_id,
            tipo_atividade_codigo=lancamento.tipo_atividade.codigo,
            tipo_atividade_nome=lancamento.tipo_atividade.nome,
            tipo_atividade_cor=lancamento.tipo_atividade.cor,
            faixa_minuto=lancamento.faixa_minuto,
            minutos=lancamento.minutos,
            descricao=lancamento.descricao,
            criado_por=lancamento.criado_por,
            atualizado_por=lancamento.atualizado_por,
            criado_em=lancamento.criado_em,
            atualizado_em=lancamento.atualizado_em,
            alertas=alertas,
        )
    except Exception as exc:
        _handle_exception(exc)


@router.put("/lancamento-admin/{lancamento_id}", summary="Editar lançamento de usuário (admin)")
def editar_lancamento_admin(
    request: Request,
    lancamento_id: int,
    body: LancamentoUpdateInput,
    admin: SomenteAdmin,
) -> LancamentoResponse:
    """Admin edita lançamento de qualquer usuário."""
    service = _get_agenda_service(request)

    try:
        lancamento, alertas = service.atualizar_lancamento(
            id=lancamento_id,
            minutos=body.minutos,
            descricao=body.descricao,
            atualizado_por=admin.usuario_id,
            eh_admin=True,
        )

        return LancamentoResponse(
            id=lancamento.id,
            usuario_id=lancamento.usuario_id,
            data_lancamento=lancamento.data_lancamento,
            bloco_id=lancamento.bloco_id,
            tipo_atividade_id=lancamento.tipo_atividade_id,
            tipo_atividade_codigo=lancamento.tipo_atividade.codigo,
            tipo_atividade_nome=lancamento.tipo_atividade.nome,
            tipo_atividade_cor=lancamento.tipo_atividade.cor,
            faixa_minuto=lancamento.faixa_minuto,
            minutos=lancamento.minutos,
            descricao=lancamento.descricao,
            criado_por=lancamento.criado_por,
            atualizado_por=lancamento.atualizado_por,
            criado_em=lancamento.criado_em,
            atualizado_em=lancamento.atualizado_em,
            alertas=alertas,
        )
    except Exception as exc:
        _handle_exception(exc)


@router.delete("/lancamento-admin/{lancamento_id}", summary="Remover lançamento de usuário (admin)")
def remover_lancamento_admin(
    request: Request,
    lancamento_id: int,
    admin: SomenteAdmin,
) -> RemovidoResponse:
    """Admin remove lançamento de qualquer usuário."""
    service = _get_agenda_service(request)

    try:
        removido = service.remover_lancamento(
            id=lancamento_id,
            removido_por=admin.usuario_id,
            eh_admin=True,
        )
        return RemovidoResponse(removido=removido)
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Rotas do Admin - Feriados
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/feriado", summary="Cadastrar feriado (admin)", status_code=201)
def criar_feriado(
    request: Request,
    body: FeriadoInput,
    admin: SomenteAdmin,
) -> FeriadoResponse:
    """Admin cadastra feriado global."""
    service = _get_agenda_service(request)

    try:
        feriado = service.criar_feriado(
            data=body.data,
            descricao=body.descricao,
            criado_por=admin.usuario_id,
        )

        return FeriadoResponse(
            id=feriado.id,
            data=feriado.data,
            descricao=feriado.descricao,
            criado_por=feriado.criado_por,
            criado_em=feriado.criado_em,
        )
    except Exception as exc:
        _handle_exception(exc)


@router.delete("/feriado/{feriado_id}", summary="Remover feriado (admin)")
def remover_feriado(
    request: Request,
    feriado_id: int,
    admin: SomenteAdmin,
) -> RemovidoResponse:
    """Admin remove feriado cadastrado."""
    service = _get_agenda_service(request)

    try:
        removido = service.remover_feriado(
            id=feriado_id,
            removido_por=admin.usuario_id,
        )
        return RemovidoResponse(removido=removido)
    except Exception as exc:
        _handle_exception(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Rotas do Admin - Indisponibilidades
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/indisponibilidade", summary="Cadastrar indisponibilidade (admin)", status_code=201)
def criar_indisponibilidade(
    request: Request,
    body: IndisponibilidadeInput,
    admin: SomenteAdmin,
) -> IndisponibilidadeResponse:
    """Admin cadastra indisponibilidade de usuário."""
    service = _get_agenda_service(request)

    try:
        indisponibilidade = service.criar_indisponibilidade(
            usuario_id=body.usuario_id,
            tipo=body.tipo,
            data_inicio=body.data_inicio,
            data_fim=body.data_fim,
            descricao=body.descricao,
            criado_por=admin.usuario_id,
        )

        return IndisponibilidadeResponse(
            id=indisponibilidade.id,
            usuario_id=indisponibilidade.usuario_id,
            tipo_atividade_id=indisponibilidade.tipo_atividade_id,
            tipo=body.tipo,
            data_inicio=indisponibilidade.data_inicio,
            data_fim=indisponibilidade.data_fim,
            descricao=indisponibilidade.descricao,
            criado_por=indisponibilidade.criado_por,
            criado_em=indisponibilidade.criado_em,
        )
    except Exception as exc:
        _handle_exception(exc)


@router.delete("/indisponibilidade/{indisponibilidade_id}", summary="Remover indisponibilidade (admin)")
def remover_indisponibilidade(
    request: Request,
    indisponibilidade_id: int,
    admin: SomenteAdmin,
) -> RemovidoResponse:
    """Admin remove indisponibilidade cadastrada."""
    service = _get_agenda_service(request)

    try:
        removido = service.remover_indisponibilidade(
            id=indisponibilidade_id,
            removido_por=admin.usuario_id,
        )
        return RemovidoResponse(removido=removido)
    except Exception as exc:
        _handle_exception(exc)
