"""Rotas de atividades e distribuicao de pontos."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import text

from cp.api.deps import UsuarioLogado

router = APIRouter(tags=["atividades"])


class TipoAtividadeResponse(BaseModel):
    id: int
    codigo: str
    nome: str
    grupo: str
    origem: str
    bloco_id: int | None = None


def _listar_tipos_fixos(request: Request) -> list[TipoAtividadeResponse]:
    engine_cp = request.app.state.engine_cp
    sql = text(
        """
        SELECT
            ta.id AS id,
            ta.codigo::text AS codigo,
            ta.nome AS nome,
            ta.grupo::text AS grupo,
            'TIPO_ATIVIDADE' AS origem,
            NULL::integer AS bloco_id
        FROM capacidade.tipo_atividade ta
        ORDER BY ta.nome
        """
    )
    with engine_cp.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [
        TipoAtividadeResponse(
            id=row.id,
            codigo=row.codigo,
            nome=row.nome,
            grupo=row.grupo,
            origem=row.origem,
            bloco_id=row.bloco_id,
        )
        for row in rows
    ]


def _listar_blocos_sincronizados(request: Request) -> list[TipoAtividadeResponse]:
    engine_cp = request.app.state.engine_cp
    with engine_cp.connect() as conn:
        tabela_existe = conn.execute(
            text("SELECT to_regclass('sap_snapshot.macrocontrole_bloco')")
        ).scalar_one_or_none()
        if not tabela_existe:
            return []

        rows = conn.execute(
            text(
                """
                SELECT
                    (1000000 + b.id) AS id,
                    'BLOCO' AS codigo,
                    b.nome AS nome,
                    'PRODUCAO' AS grupo,
                    'BLOCO' AS origem,
                    b.id AS bloco_id
                FROM sap_snapshot.macrocontrole_bloco b
                ORDER BY b.nome
                """
            )
        ).fetchall()

    return [
        TipoAtividadeResponse(
            id=row.id,
            codigo=row.codigo,
            nome=row.nome,
            grupo=row.grupo,
            origem=row.origem,
            bloco_id=row.bloco_id,
        )
        for row in rows
    ]


@router.get("/atividades/tipos", summary="Tipos de atividade e blocos sincronizados")
def listar_tipos_atividade(_: UsuarioLogado, request: Request) -> list[TipoAtividadeResponse]:
    tipos = _listar_tipos_fixos(request)
    try:
        blocos = _listar_blocos_sincronizados(request)
    except Exception:
        blocos = []
    return [*tipos, *blocos]


class AtividadeResumo(BaseModel):
    id: int
    ut_id: int
    tipo_etapa_id: int
    tipo_etapa_nome: str
    tipo_situacao_id: int
    tipo_situacao_nome: str
    usuario_id: int | None
    usuario_nome: str | None
    data_inicio: str | None
    data_fim: str | None


class AtividadesResponse(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    itens: list[AtividadeResumo]


@router.get("/atividades", summary="Listagem filtrada de atividades")
def listar_atividades(
    _: UsuarioLogado,
    projeto_id: int | None = Query(None),
    subfase_id: int | None = Query(None),
    usuario_id: int | None = Query(None),
    tipo_etapa_id: int | None = Query(None),
    tipo_situacao_id: int | None = Query(None),
    data_inicio: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    data_fim: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=500),
) -> AtividadesResponse:
    return AtividadesResponse(total=0, pagina=pagina, por_pagina=por_pagina, itens=[])


class AtividadeDetalhe(BaseModel):
    id: int
    ut_id: int
    tipo_etapa_id: int
    tipo_etapa_nome: str
    tipo_situacao_id: int
    tipo_situacao_nome: str
    usuario_id: int | None
    usuario_nome: str | None
    data_inicio: str | None
    data_fim: str | None
    observacao: str | None
    nota_qualidade: int | None
    texto_qualidade: str | None


@router.get("/atividades/{atividade_id}", summary="Detalhe de uma atividade")
def detalhe_atividade(atividade_id: int, _: UsuarioLogado) -> AtividadeDetalhe:
    return AtividadeDetalhe(
        id=atividade_id,
        ut_id=0,
        tipo_etapa_id=0,
        tipo_etapa_nome="",
        tipo_situacao_id=0,
        tipo_situacao_nome="",
        usuario_id=None,
        usuario_nome=None,
        data_inicio=None,
        data_fim=None,
        observacao=None,
        nota_qualidade=None,
        texto_qualidade=None,
    )


class DistribuicaoPontos(BaseModel):
    projeto_nome: str | None
    subfase_nome: str | None
    ut_id: int
    pontos_ut: float | None
    ciclo_modelo: str
    nota: int | None
    nota_valida: bool
    nome_executor: str | None
    pontos_executor: float | None
    nome_corretor: str | None
    pontos_corretor: float | None
    nome_revisor: str | None
    pontos_revisor: float | None


class DistribuicaoPontosResponse(BaseModel):
    total: int
    sap_snapshot_atualizado_em: str | None
    itens: list[DistribuicaoPontos]


@router.get("/distribuicao-pontos", summary="Distribuicao de pontos por UT concluida")
def distribuicao_pontos(
    _: UsuarioLogado,
    projeto_id: int | None = Query(None),
    subfase_id: int | None = Query(None),
    usuario_id: int | None = Query(None),
) -> DistribuicaoPontosResponse:
    return DistribuicaoPontosResponse(total=0, sap_snapshot_atualizado_em=None, itens=[])
