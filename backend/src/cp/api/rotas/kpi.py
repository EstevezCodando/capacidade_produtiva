"""Rotas de KPI e progresso de producao.

Politica de autorizacao:
    GET /kpi/projetos              — autenticado
    GET /kpi/projetos/{id}         — autenticado
    GET /kpi/subfase/{id}          — autenticado
    GET /kpi/uts/{id}              — autenticado
    GET /kpi/inconsistencias       — admin
    GET /kpi/dashboard             — autenticado (novo - dashboard completo)
    GET /kpi/meu-dashboard             — autenticado (dashboard do operador)
"""

from __future__ import annotations

import calendar
import logging
from typing import Any

from datetime import date
from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

from cp.api.deps import SomenteAdmin, UsuarioLogado

router = APIRouter(prefix="/kpi", tags=["kpi"])
_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_sync_timestamps(engine_cp: Any) -> tuple[str | None, str | None]:
    """Retorna timestamps de snapshot e KPI."""
    snapshot_ts = None
    kpi_ts = None

    try:
        with engine_cp.connect() as conn:
            # Timestamp do snapshot
            result = conn.execute(
                text("""
                SELECT MAX(data_fim) FROM sap_snapshot.macrocontrole_atividade
                WHERE data_fim IS NOT NULL
            """)
            )
            row = result.fetchone()
            if row and row[0]:
                snapshot_ts = row[0].isoformat()

            # Verifica se KPI foi calculado
            result = conn.execute(text("SELECT COUNT(*) FROM kpi.estado_ut"))
            row = result.fetchone()
            if row and row[0] > 0:
                kpi_ts = snapshot_ts  # Usa mesmo timestamp por simplicidade
    except Exception:
        _logger.debug("Não foi possível obter timestamps de sync", exc_info=True)

    return snapshot_ts, kpi_ts


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------


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


class KpiLote(BaseModel):
    lote_id: int
    lote_nome: str
    blocos: list[KpiBloco]


class KpiProjetoDetalhe(BaseModel):
    projeto_id: int
    projeto_nome: str
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None
    lotes: list[KpiLote]
    blocos: list[KpiBloco]  # Mantido para compatibilidade


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


# ---------------------------------------------------------------------------
# Dashboard Models
# ---------------------------------------------------------------------------


class MesTrilhaResposta(BaseModel):
    """Ponto mensal da timeline acumulada de horas."""

    mes: str                           # "YYYY-MM-DD" — 1º dia do mês
    minutos_previstos_acum: int        # J: previsto acumulado até este mês
    minutos_lancados_normal_acum: int  # K: lançado horário normal acumulado
    minutos_lancados_total_acum: int   # P: lançado normal + extra acumulado
    minutos_divergente_acum: int = 0   # D: horas fora do bloco selecionado (só com filtro)


class TopUsuario(BaseModel):
    usuario_id: int
    nome: str
    nome_guerra: str | None
    pontos: float


class SubfaseProgresso(BaseModel):
    subfase_id: int
    subfase_nome: str
    fase_nome: str
    pontos_total: float
    pontos_realizados: float
    progresso: float | None
    cor: str | None


class BlocoHierarquia(BaseModel):
    bloco_id: int
    bloco_nome: str
    subfases: list[SubfaseProgresso]


class LoteHierarquia(BaseModel):
    lote_id: int
    lote_nome: str
    blocos: list[BlocoHierarquia]


class ProjetoHierarquia(BaseModel):
    projeto_id: int
    projeto_nome: str
    lotes: list[LoteHierarquia]


class ContribuidorBloco(BaseModel):
    """Top performer em um bloco (executor ou revisor)."""
    usuario_id: int
    nome_guerra: str
    pontos: float
    percentual: float  # % dos pontos totais do bloco


class BlocoDestaque(BaseModel):
    """Resumo de progresso e top performers de um bloco."""
    bloco_id: int
    bloco_nome: str
    projeto_nome: str
    lote_nome: str
    uts_total: int
    uts_concluidas: int
    uts_em_andamento: int
    uts_sem_inicio: int
    pontos_total: float
    pontos_realizados: float
    progresso: float | None
    top_executores: list[ContribuidorBloco]
    top_revisores: list[ContribuidorBloco]


class AlertaNotaAusente(BaseModel):
    """UT concluída com nota ausente ou inválida."""
    ut_id: int
    bloco_nome: str
    lote_nome: str
    subfase_nome: str
    executor_id: int | None
    nome_executor: str | None
    revisor_id: int | None
    nome_revisor: str | None
    cor_atividade_id: int | None  # ID da atividade de correção (kpi.fluxo_ut)
    ocorrencia: str  # NOTA_AUSENTE | NOTA_INVALIDA


class RankingOperador(BaseModel):
    """Posição no ranking global de produção."""
    posicao: int
    usuario_id: int
    nome_guerra: str
    pontos_executor: float
    pontos_revisor: float
    pontos_corretor: float
    pontos_total: float
    uts_executadas: int
    uts_revisadas: int


class SemanaVelocidade(BaseModel):
    """UTs concluídas e pontos realizados em uma semana."""
    semana_label: str   # "DD/MM"
    semana_inicio: str  # "YYYY-MM-DD"
    uts_concluidas: int
    pontos_realizados: float


class DistribuicaoCiclo(BaseModel):
    """Distribuição de UTs por modelo de ciclo."""
    ciclo: str
    quantidade: int
    percentual: float


class DashboardResponse(BaseModel):
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None
    projetos_ativos: int
    blocos_sap_cadastrados: int
    progresso_geral: float | None
    pontos_totais: float
    pontos_realizados: float
    horas_previstas_producao_min: int
    horas_lancadas_producao_min: int
    hierarquia: list[ProjetoHierarquia]
    top_executor: TopUsuario | None
    top_revisor: TopUsuario | None
    top_executores_subfase: list[dict[str, Any]]
    top_revisores_subfase: list[dict[str, Any]]
    timeline_mensal: list[MesTrilhaResposta] = []
    # ── Novos campos de controle gerencial ────────────────────
    blocos_destaque: list[BlocoDestaque] = []
    alertas_nota: list[AlertaNotaAusente] = []
    ranking_operadores: list[RankingOperador] = []
    velocidade_semanal: list[SemanaVelocidade] = []
    distribuicao_ciclos: list[DistribuicaoCiclo] = []
    # ── Filtros ativos ────────────────────────────────────────
    bloco_filtro_id: int | None = None
    bloco_filtro_nome: str | None = None
    subfase_filtro_id: int | None = None
    subfase_filtro_nome: str | None = None
    # Lista de subfases disponíveis (para selector no frontend)
    subfases_disponiveis: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------


@router.get("/projetos", summary="KPI agregado por projeto")
def kpi_projetos(_: UsuarioLogado, request: Request, response: Response) -> KpiProjetosResponse:
    """Progresso percentual, pontos totais e concluidos por projeto ativo."""
    engine_cp = request.app.state.engine_cp
    snapshot_ts, kpi_ts = _get_sync_timestamps(engine_cp)

    projetos = []
    try:
        with engine_cp.connect() as conn:
            # Busca projetos com agregação de pontos
            sql = text("""
                SELECT 
                    p.id as projeto_id,
                    p.nome,
                    COALESCE(SUM(e.ut_dificuldade), 0) as pontos_total,
                    COALESCE(SUM(
                        COALESCE(d.pontos_executor, 0) + 
                        COALESCE(d.pontos_revisor, 0) + 
                        COALESCE(d.pontos_corretor, 0)
                    ), 0) as pontos_concluidos
                FROM sap_snapshot.macrocontrole_projeto p
                LEFT JOIN sap_snapshot.macrocontrole_lote l ON l.projeto_id = p.id
                LEFT JOIN sap_snapshot.macrocontrole_bloco b ON b.lote_id = l.id
                LEFT JOIN sap_snapshot.macrocontrole_unidade_trabalho ut ON ut.bloco_id = b.id
                LEFT JOIN kpi.estado_ut e ON e.ut_id = ut.id
                LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = ut.id
                WHERE p.status_id = 1  -- Projetos ativos
                GROUP BY p.id, p.nome
                ORDER BY p.nome
            """)
            result = conn.execute(sql)
            for row in result:
                pontos_total = float(row.pontos_total or 0)
                pontos_concluidos = float(row.pontos_concluidos or 0)
                progresso = (pontos_concluidos / pontos_total * 100) if pontos_total > 0 else None

                projetos.append(
                    KpiProjeto(
                        projeto_id=row.projeto_id,
                        nome=row.nome,
                        progresso=round(progresso, 2) if progresso else None,
                        pontos_total=pontos_total,
                        pontos_concluidos=pontos_concluidos,
                        sap_snapshot_atualizado_em=snapshot_ts,
                        kpi_calculado_em=kpi_ts,
                    )
                )
    except Exception:
        _logger.exception("Erro ao buscar projetos KPI")
        raise HTTPException(status_code=500, detail="Erro ao buscar projetos KPI")

    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=30"
    return KpiProjetosResponse(
        sap_snapshot_atualizado_em=snapshot_ts,
        kpi_calculado_em=kpi_ts,
        projetos=projetos,
    )


@router.get("/projetos/{projeto_id}", summary="KPI do projeto por bloco e subfase")
def kpi_projeto_detalhe(projeto_id: int, _: UsuarioLogado, request: Request, response: Response) -> KpiProjetoDetalhe:
    """Drill-down do projeto: progresso por lote, bloco e subfase."""
    engine_cp = request.app.state.engine_cp
    snapshot_ts, kpi_ts = _get_sync_timestamps(engine_cp)

    projeto_nome = ""
    lotes_dict: dict[int, dict[str, Any]] = {}
    blocos_list = []

    try:
        with engine_cp.connect() as conn:
            # Nome do projeto
            result = conn.execute(text("SELECT nome FROM sap_snapshot.macrocontrole_projeto WHERE id = :id"), {"id": projeto_id})
            row = result.fetchone()
            if row:
                projeto_nome = row.nome

            # Agregação por lote -> bloco -> subfase
            sql = text("""
                SELECT 
                    l.id as lote_id,
                    l.nome as lote_nome,
                    b.id as bloco_id,
                    b.nome as bloco_nome,
                    sf.id as subfase_id,
                    sf.nome as subfase_nome,
                    COALESCE(SUM(e.ut_dificuldade), 0) as pontos_total,
                    COALESCE(SUM(
                        COALESCE(d.pontos_executor, 0) + 
                        COALESCE(d.pontos_revisor, 0) + 
                        COALESCE(d.pontos_corretor, 0)
                    ), 0) as pontos_concluidos
                FROM sap_snapshot.macrocontrole_lote l
                JOIN sap_snapshot.macrocontrole_bloco b ON b.lote_id = l.id
                JOIN sap_snapshot.macrocontrole_unidade_trabalho ut ON ut.bloco_id = b.id
                JOIN sap_snapshot.macrocontrole_subfase sf ON sf.id = ut.subfase_id
                LEFT JOIN kpi.estado_ut e ON e.ut_id = ut.id
                LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = ut.id
                WHERE l.projeto_id = :projeto_id
                GROUP BY l.id, l.nome, b.id, b.nome, sf.id, sf.nome
                ORDER BY l.nome, b.nome, sf.nome
            """)
            result = conn.execute(sql, {"projeto_id": projeto_id})

            blocos_dict: dict[int, dict[str, Any]] = {}

            for row in result:
                pontos_total = float(row.pontos_total or 0)
                pontos_concluidos = float(row.pontos_concluidos or 0)
                progresso = (pontos_concluidos / pontos_total * 100) if pontos_total > 0 else None

                subfase = KpiSubfase(
                    subfase_id=row.subfase_id,
                    subfase_nome=row.subfase_nome,
                    progresso=round(progresso, 2) if progresso else None,
                    pontos_total=pontos_total,
                    pontos_concluidos=pontos_concluidos,
                )

                # Organiza em lotes
                if row.lote_id not in lotes_dict:
                    lotes_dict[row.lote_id] = {
                        "lote_id": row.lote_id,
                        "lote_nome": row.lote_nome,
                        "blocos": {},
                    }

                lote = lotes_dict[row.lote_id]
                if row.bloco_id not in lote["blocos"]:
                    lote["blocos"][row.bloco_id] = {
                        "bloco_id": row.bloco_id,
                        "bloco_nome": row.bloco_nome,
                        "subfases": [],
                    }

                lote["blocos"][row.bloco_id]["subfases"].append(subfase)

                # Também mantém lista flat de blocos para compatibilidade
                if row.bloco_id not in blocos_dict:
                    blocos_dict[row.bloco_id] = {
                        "bloco_id": row.bloco_id,
                        "bloco_nome": row.bloco_nome,
                        "subfases": [],
                    }
                blocos_dict[row.bloco_id]["subfases"].append(subfase)

            # Converte para listas
            lotes = [
                KpiLote(
                    lote_id=lote_item["lote_id"],
                    lote_nome=lote_item["lote_nome"],
                    blocos=[
                        KpiBloco(
                            bloco_id=bloco["bloco_id"],
                            bloco_nome=bloco["bloco_nome"],
                            subfases=bloco["subfases"],
                        )
                        for bloco in lote_item["blocos"].values()
                    ],
                )
                for lote_item in lotes_dict.values()
            ]

            blocos_list = [
                KpiBloco(
                    bloco_id=b["bloco_id"],
                    bloco_nome=b["bloco_nome"],
                    subfases=b["subfases"],
                )
                for b in blocos_dict.values()
            ]
    except Exception:
        _logger.exception("Erro ao buscar detalhe do projeto projeto_id=%s", projeto_id)
        raise HTTPException(status_code=500, detail="Erro ao buscar detalhe do projeto")

    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=30"
    return KpiProjetoDetalhe(
        projeto_id=projeto_id,
        projeto_nome=projeto_nome,
        sap_snapshot_atualizado_em=snapshot_ts,
        kpi_calculado_em=kpi_ts,
        lotes=lotes if "lotes" in dir() else [],
        blocos=blocos_list,
    )


@router.get("/subfase/{subfase_id}", summary="UTs de uma subfase")
def kpi_subfase(subfase_id: int, _: UsuarioLogado, request: Request, response: Response) -> KpiSubfaseDetalhe:
    """Listagem completa das UTs da subfase com estado, ciclo, nota e pontos."""
    engine_cp = request.app.state.engine_cp
    snapshot_ts, kpi_ts = _get_sync_timestamps(engine_cp)

    subfase_nome = ""
    uts = []

    try:
        with engine_cp.connect() as conn:
            # Nome da subfase
            result = conn.execute(text("SELECT nome FROM sap_snapshot.macrocontrole_subfase WHERE id = :id"), {"id": subfase_id})
            row = result.fetchone()
            if row:
                subfase_nome = row.nome

            # UTs da subfase
            sql = text("""
                SELECT 
                    e.ut_id,
                    COALESCE(e.estado_ut_subfase, 'desconhecido') as estado_ut_subfase,
                    COALESCE(e.ciclo_modelo, 'desconhecido') as ciclo_modelo,
                    d.nota_final as nota_qualidade,
                    COALESCE(e.ocorrencia, 'OK') as ocorrencia,
                    d.pontos_executor,
                    d.pontos_revisor,
                    d.pontos_corretor,
                    d.nome_executor,
                    d.nome_revisor,
                    d.nome_corretor,
                    e.data_inicio_fluxo,
                    e.data_fim_fluxo
                FROM kpi.estado_ut e
                LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = e.ut_id
                WHERE e.subfase_id = :subfase_id
                ORDER BY e.ut_id
            """)
            result = conn.execute(sql, {"subfase_id": subfase_id})

            for row in result:
                uts.append(
                    KpiUt(
                        ut_id=row.ut_id,
                        estado_ut_subfase=row.estado_ut_subfase,
                        ciclo_modelo=row.ciclo_modelo,
                        nota_qualidade=row.nota_qualidade,
                        ocorrencia=row.ocorrencia,
                        pontos_executor=float(row.pontos_executor) if row.pontos_executor else None,
                        pontos_revisor=float(row.pontos_revisor) if row.pontos_revisor else None,
                        pontos_corretor=float(row.pontos_corretor) if row.pontos_corretor else None,
                        nome_executor=row.nome_executor,
                        nome_revisor=row.nome_revisor,
                        nome_corretor=row.nome_corretor,
                        data_inicio_fluxo=row.data_inicio_fluxo.isoformat() if row.data_inicio_fluxo else None,
                        data_fim_fluxo=row.data_fim_fluxo.isoformat() if row.data_fim_fluxo else None,
                    )
                )
    except Exception:
        _logger.exception("Erro ao buscar UTs da subfase subfase_id=%s", subfase_id)
        raise HTTPException(status_code=500, detail="Erro ao buscar dados da subfase")

    response.headers["Cache-Control"] = "private, max-age=30, stale-while-revalidate=15"
    return KpiSubfaseDetalhe(
        subfase_id=subfase_id,
        subfase_nome=subfase_nome,
        sap_snapshot_atualizado_em=snapshot_ts,
        kpi_calculado_em=kpi_ts,
        uts=uts,
    )


@router.get("/uts/{ut_id}", summary="Detalhe completo de uma UT")
def kpi_ut(ut_id: int, _: UsuarioLogado, request: Request, response: Response) -> KpiUtDetalhe:
    """Estado completo da UT: ciclo, fluxo, nota, participantes e pontos."""
    engine_cp = request.app.state.engine_cp
    snapshot_ts, kpi_ts = _get_sync_timestamps(engine_cp)

    try:
        with engine_cp.connect() as conn:
            sql = text("""
                SELECT 
                    e.ut_id,
                    COALESCE(e.ciclo_modelo, 'desconhecido') as ciclo_modelo,
                    COALESCE(e.estado_ut_subfase, 'desconhecido') as estado_ut_subfase,
                    e.concluida,
                    d.nota_final as nota_qualidade,
                    d.texto_nota as texto_qualidade,
                    COALESCE(e.ocorrencia, 'OK') as ocorrencia,
                    e.data_inicio_fluxo,
                    e.data_fim_fluxo,
                    e.ut_dificuldade as pontos_ut,
                    d.pontos_executor,
                    d.pontos_revisor,
                    d.pontos_corretor,
                    d.nome_executor,
                    d.nome_revisor,
                    d.nome_corretor
                FROM kpi.estado_ut e
                LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = e.ut_id
                WHERE e.ut_id = :ut_id
            """)
            result = conn.execute(sql, {"ut_id": ut_id})
            row = result.fetchone()

            if row:
                return KpiUtDetalhe(
                    ut_id=row.ut_id,
                    ciclo_modelo=row.ciclo_modelo,
                    estado_ut_subfase=row.estado_ut_subfase,
                    concluida=row.concluida or False,
                    nota_qualidade=row.nota_qualidade,
                    texto_qualidade=row.texto_qualidade,
                    ocorrencia=row.ocorrencia,
                    data_inicio_fluxo=row.data_inicio_fluxo.isoformat() if row.data_inicio_fluxo else None,
                    data_fim_fluxo=row.data_fim_fluxo.isoformat() if row.data_fim_fluxo else None,
                    pontos_ut=float(row.pontos_ut) if row.pontos_ut else None,
                    pontos_executor=float(row.pontos_executor) if row.pontos_executor else None,
                    pontos_revisor=float(row.pontos_revisor) if row.pontos_revisor else None,
                    pontos_corretor=float(row.pontos_corretor) if row.pontos_corretor else None,
                    nome_executor=row.nome_executor,
                    nome_revisor=row.nome_revisor,
                    nome_corretor=row.nome_corretor,
                    sap_snapshot_atualizado_em=snapshot_ts,
                    kpi_calculado_em=kpi_ts,
                )
    except Exception:
        _logger.exception("Erro ao buscar detalhe da UT ut_id=%s", ut_id)
        raise HTTPException(status_code=500, detail="Erro ao buscar detalhe da UT")

    response.headers["Cache-Control"] = "private, max-age=30, stale-while-revalidate=15"
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
        sap_snapshot_atualizado_em=snapshot_ts,
        kpi_calculado_em=kpi_ts,
    )


@router.get("/inconsistencias", summary="Alertas e inconsistencias de nota e ciclo")
def kpi_inconsistencias(_: SomenteAdmin, request: Request, response: Response) -> InconsistenciasResponse:
    """UTs com NOTA_AUSENTE, NOTA_INVALIDA, INCONSISTENTE_CICLO ou INCONSISTENTE_DIFICULDADE."""
    engine_cp = request.app.state.engine_cp
    snapshot_ts, kpi_ts = _get_sync_timestamps(engine_cp)

    itens = []
    try:
        with engine_cp.connect() as conn:
            sql = text("""
                SELECT 
                    e.ut_id,
                    e.ocorrencia,
                    e.projeto_nome,
                    e.subfase_nome,
                    e.ciclo_modelo,
                    d.nome_executor
                FROM kpi.estado_ut e
                LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = e.ut_id
                WHERE e.ocorrencia IS NOT NULL 
                  AND e.ocorrencia NOT IN ('OK', 'CONCLUIDA')
                ORDER BY e.projeto_nome, e.subfase_nome, e.ut_id
                LIMIT 500
            """)
            result = conn.execute(sql)

            for row in result:
                itens.append(
                    Inconsistencia(
                        ut_id=row.ut_id,
                        ocorrencia=row.ocorrencia or "",
                        projeto_nome=row.projeto_nome,
                        subfase_nome=row.subfase_nome,
                        ciclo_modelo=row.ciclo_modelo or "",
                        nome_executor=row.nome_executor,
                    )
                )
    except Exception:
        _logger.exception("Erro ao buscar inconsistencias KPI")
        raise HTTPException(status_code=500, detail="Erro ao buscar inconsistências")

    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=30"
    return InconsistenciasResponse(
        total=len(itens),
        sap_snapshot_atualizado_em=snapshot_ts,
        itens=itens,
    )


@router.get("/dashboard", summary="Dashboard completo com hierarquia e destaques")
def kpi_dashboard(
    _: UsuarioLogado,
    request: Request,
    response: Response,
    bloco_id: int | None = Query(None, description="Filtrar dashboard por bloco específico"),
    subfase_id: int | None = Query(None, description="Filtrar ranking por subfase"),
) -> DashboardResponse:
    """Dashboard consolidado com progresso geral, hierarquia de projetos e top performers.

    Quando bloco_id é fornecido, todos os widgets são filtrados para aquele bloco,
    e a timeline exibe a série D (horas lançadas fora do contexto planejado).
    """
    engine_cp = request.app.state.engine_cp
    snapshot_ts, kpi_ts = _get_sync_timestamps(engine_cp)

    projetos_ativos = 0
    pontos_totais = 0.0
    pontos_realizados = 0.0
    blocos_sap_cadastrados = 0
    horas_previstas_producao_min = 0
    horas_lancadas_producao_min = 0
    hierarquia: list[ProjetoHierarquia] = []
    top_executor: TopUsuario | None = None
    top_revisor: TopUsuario | None = None
    top_executores_subfase: list[dict[str, Any]] = []
    top_revisores_subfase: list[dict[str, Any]] = []
    timeline_mensal: list[MesTrilhaResposta] = []
    blocos_destaque: list[BlocoDestaque] = []
    alertas_nota: list[AlertaNotaAusente] = []
    ranking_operadores: list[RankingOperador] = []
    velocidade_semanal: list[SemanaVelocidade] = []
    distribuicao_ciclos: list[DistribuicaoCiclo] = []
    bloco_filtro_nome: str | None = None
    subfase_filtro_nome: str | None = None
    subfases_disponiveis: list[dict[str, Any]] = []

    # Helpers de filtro — injetados nos SQLs quando bloco_id está ativo
    bloco_cond_e = "AND e.bloco_id = :bloco_id" if bloco_id else ""
    bloco_cond_d = "AND d.bloco_id = :bloco_id" if bloco_id else ""
    bp = {"bloco_id": bloco_id} if bloco_id else {}
    # Subfase filter — somente para o ranking (via JOIN com estado_ut)
    bp_rank = {**bp, "subfase_id": subfase_id} if subfase_id else bp

    try:
        with engine_cp.connect() as conn:
            # 0. Resolve nome do bloco filtrado (se houver)
            if bloco_id:
                r = conn.execute(
                    text("SELECT nome FROM sap_snapshot.macrocontrole_bloco WHERE id = :bid"),
                    {"bid": bloco_id},
                ).fetchone()
                bloco_filtro_nome = r.nome if r else None

            # 1. Contagem de projetos ativos
            result = conn.execute(text("SELECT COUNT(*) FROM sap_snapshot.macrocontrole_projeto WHERE status_id = 1"))
            row = result.fetchone()
            projetos_ativos = row[0] if row else 0

            # 1.1. Contagem de blocos cadastrados no snapshot SAP
            result = conn.execute(text("SELECT COUNT(*) FROM sap_snapshot.macrocontrole_bloco"))
            row = result.fetchone()
            blocos_sap_cadastrados = int(row[0]) if row else 0

            # 1.2. Horas previstas e horas lançadas em produção (bloco)
            _bloco_filter_ap = "AND ap.bloco_id = :bloco_id" if bloco_id else "AND ap.bloco_id IS NOT NULL"
            _bloco_filter_al = "AND al.bloco_id = :bloco_id" if bloco_id else "AND ta.codigo = 'BLOCO'"
            result = conn.execute(
                text(f"""
                SELECT
                    COALESCE(SUM(ap.minutos_planejados_normais + ap.minutos_planejados_extras), 0) AS horas_previstas_producao_min,
                    COALESCE((
                        SELECT SUM(al.minutos)
                        FROM capacidade.agenda_lancamento al
                        LEFT JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id
                        WHERE al.em_uso = TRUE
                          {_bloco_filter_al}
                    ), 0) AS horas_lancadas_producao_min
                FROM capacidade.agenda_prevista_admin ap
                WHERE ap.em_uso = TRUE
                  {_bloco_filter_ap}
                """),
                bp,
            )
            row = result.fetchone()
            if row:
                horas_previstas_producao_min = int(row.horas_previstas_producao_min or 0)
                horas_lancadas_producao_min = int(row.horas_lancadas_producao_min or 0)

            # 2. Pontos totais e realizados
            result = conn.execute(
                text(f"""
                SELECT
                    COALESCE(SUM(e.ut_dificuldade), 0) as pontos_totais,
                    COALESCE(SUM(
                        COALESCE(d.pontos_executor, 0) +
                        COALESCE(d.pontos_revisor, 0) +
                        COALESCE(d.pontos_corretor, 0)
                    ), 0) as pontos_realizados
                FROM kpi.estado_ut e
                LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = e.ut_id
                WHERE TRUE {bloco_cond_e}
            """),
                bp,
            )
            row = result.fetchone()
            if row:
                pontos_totais = float(row.pontos_totais or 0)
                pontos_realizados = float(row.pontos_realizados or 0)

            # 3. Hierarquia: Projeto -> Lote -> Bloco -> Subfase
            _bloco_hier = "AND b.id = :bloco_id" if bloco_id else ""
            sql = text(f"""
                SELECT
                    p.id as projeto_id,
                    p.nome as projeto_nome,
                    l.id as lote_id,
                    l.nome as lote_nome,
                    b.id as bloco_id,
                    b.nome as bloco_nome,
                    sf.id as subfase_id,
                    sf.nome as subfase_nome,
                    tf.nome as fase_nome,
                    tf.cor as fase_cor,
                    COALESCE(SUM(e.ut_dificuldade), 0) as pontos_total,
                    COALESCE(SUM(
                        COALESCE(d.pontos_executor, 0) +
                        COALESCE(d.pontos_revisor, 0) +
                        COALESCE(d.pontos_corretor, 0)
                    ), 0) as pontos_realizados
                FROM sap_snapshot.macrocontrole_projeto p
                JOIN sap_snapshot.macrocontrole_lote l ON l.projeto_id = p.id
                JOIN sap_snapshot.macrocontrole_bloco b ON b.lote_id = l.id
                JOIN sap_snapshot.macrocontrole_unidade_trabalho ut ON ut.bloco_id = b.id
                JOIN sap_snapshot.macrocontrole_subfase sf ON sf.id = ut.subfase_id
                JOIN sap_snapshot.macrocontrole_fase f ON f.id = sf.fase_id
                JOIN sap_snapshot.dominio_tipo_fase tf ON tf.code = f.tipo_fase_id
                LEFT JOIN kpi.estado_ut e ON e.ut_id = ut.id
                LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = ut.id
                WHERE p.status_id = 1 {_bloco_hier}
                GROUP BY p.id, p.nome, l.id, l.nome, b.id, b.nome, sf.id, sf.nome, tf.nome, tf.cor
                ORDER BY p.nome, l.nome, b.nome, sf.nome
            """)
            result = conn.execute(sql, bp)

            projetos_dict: dict[int, dict[str, Any]] = {}
            for row in result:
                pt = float(row.pontos_total or 0)
                pr = float(row.pontos_realizados or 0)
                prog = (pr / pt * 100) if pt > 0 else None

                subfase = SubfaseProgresso(
                    subfase_id=row.subfase_id,
                    subfase_nome=row.subfase_nome,
                    fase_nome=row.fase_nome,
                    pontos_total=pt,
                    pontos_realizados=pr,
                    progresso=round(prog, 2) if prog else None,
                    cor=row.fase_cor,
                )

                # Organiza hierarquia
                if row.projeto_id not in projetos_dict:
                    projetos_dict[row.projeto_id] = {
                        "projeto_id": row.projeto_id,
                        "projeto_nome": row.projeto_nome,
                        "lotes": {},
                    }

                proj = projetos_dict[row.projeto_id]
                if row.lote_id not in proj["lotes"]:
                    proj["lotes"][row.lote_id] = {
                        "lote_id": row.lote_id,
                        "lote_nome": row.lote_nome,
                        "blocos": {},
                    }

                lote = proj["lotes"][row.lote_id]
                if row.bloco_id not in lote["blocos"]:
                    lote["blocos"][row.bloco_id] = {
                        "bloco_id": row.bloco_id,
                        "bloco_nome": row.bloco_nome,
                        "subfases": [],
                    }

                lote["blocos"][row.bloco_id]["subfases"].append(subfase)

            # Converte hierarquia
            for proj_item in projetos_dict.values():
                hierarquia.append(
                    ProjetoHierarquia(
                        projeto_id=proj_item["projeto_id"],
                        projeto_nome=proj_item["projeto_nome"],
                        lotes=[
                            LoteHierarquia(
                                lote_id=lote_item["lote_id"],
                                lote_nome=lote_item["lote_nome"],
                                blocos=[
                                    BlocoHierarquia(
                                        bloco_id=bloco["bloco_id"],
                                        bloco_nome=bloco["bloco_nome"],
                                        subfases=bloco["subfases"],
                                    )
                                    for bloco in lote_item["blocos"].values()
                                ],
                            )
                            for lote_item in proj_item["lotes"].values()
                        ],
                    )
                )

            # 4. Top executor
            sql = text(f"""
                SELECT
                    u.id as usuario_id,
                    u.nome,
                    u.nome_guerra,
                    SUM(d.pontos_executor) as pontos
                FROM kpi.distribuicao_pontos d
                JOIN sap_snapshot.dgeo_usuario u ON u.id = d.executor_id
                WHERE d.pontos_executor > 0 {bloco_cond_d}
                GROUP BY u.id, u.nome, u.nome_guerra
                ORDER BY pontos DESC
                LIMIT 1
            """)
            result = conn.execute(sql, bp)
            row = result.fetchone()
            if row:
                top_executor = TopUsuario(
                    usuario_id=row.usuario_id,
                    nome=row.nome,
                    nome_guerra=row.nome_guerra,
                    pontos=float(row.pontos),
                )

            # 5. Top revisor
            sql = text(f"""
                SELECT
                    u.id as usuario_id,
                    u.nome,
                    u.nome_guerra,
                    SUM(d.pontos_revisor) as pontos
                FROM kpi.distribuicao_pontos d
                JOIN sap_snapshot.dgeo_usuario u ON u.id = d.revisor_id
                WHERE d.pontos_revisor > 0 {bloco_cond_d}
                GROUP BY u.id, u.nome, u.nome_guerra
                ORDER BY pontos DESC
                LIMIT 1
            """)
            result = conn.execute(sql, bp)
            row = result.fetchone()
            if row:
                top_revisor = TopUsuario(
                    usuario_id=row.usuario_id,
                    nome=row.nome,
                    nome_guerra=row.nome_guerra,
                    pontos=float(row.pontos),
                )

            # 6. Busca os Top Executores por Subfase
            sql_exec = text(f"""
                WITH ranking AS (
                    SELECT
                        e.subfase_id, e.subfase_nome, d.executor_id as usr_id, u.nome, u.nome_guerra,
                        SUM(d.pontos_executor) as pontos,
                        ROW_NUMBER() OVER(PARTITION BY e.subfase_id ORDER BY SUM(d.pontos_executor) DESC) as rn
                    FROM kpi.estado_ut e
                    JOIN kpi.distribuicao_pontos d ON e.ut_id = d.ut_id
                    JOIN sap_snapshot.dgeo_usuario u ON u.id = d.executor_id
                    WHERE d.pontos_executor > 0 {bloco_cond_e}
                    GROUP BY e.subfase_id, e.subfase_nome, d.executor_id, u.nome, u.nome_guerra
                )
                SELECT subfase_id, subfase_nome, usr_id, nome, nome_guerra, pontos
                FROM ranking WHERE rn = 1
            """)
            for row in conn.execute(sql_exec, bp):
                top_executores_subfase.append(
                    {
                        "subfase_id": row.subfase_id,
                        "usuario_id": row.usr_id,
                        "nome": row.nome,
                        "nome_guerra": row.nome_guerra,
                        "pontos": float(row.pontos),
                    }
                )

            # 7. Busca os Top Revisores por Subfase
            sql_rev = text(f"""
                WITH ranking AS (
                    SELECT
                        e.subfase_id, e.subfase_nome, d.revisor_id as usr_id, u.nome, u.nome_guerra,
                        SUM(d.pontos_revisor) as pontos,
                        ROW_NUMBER() OVER(PARTITION BY e.subfase_id ORDER BY SUM(d.pontos_revisor) DESC) as rn
                    FROM kpi.estado_ut e
                    JOIN kpi.distribuicao_pontos d ON e.ut_id = d.ut_id
                    JOIN sap_snapshot.dgeo_usuario u ON u.id = d.revisor_id
                    WHERE d.pontos_revisor > 0 {bloco_cond_e}
                    GROUP BY e.subfase_id, e.subfase_nome, d.revisor_id, u.nome, u.nome_guerra
                )
                SELECT subfase_id, subfase_nome, usr_id, nome, nome_guerra, pontos
                FROM ranking WHERE rn = 1
            """)
            for row in conn.execute(sql_rev, bp):
                top_revisores_subfase.append(
                    {
                        "subfase_id": row.subfase_id,
                        "usuario_id": row.usr_id,
                        "nome": row.nome,
                        "nome_guerra": row.nome_guerra,
                        "pontos": float(row.pontos),
                    }
                )

            # 8. Timeline mensal acumulada — J (previsto), K (normal), P (total), D (divergente)
            # Sempre gera exatamente 12 meses para garantir que o gráfico seja exibido.
            # Quando bloco_id ativo: filtra por bloco e calcula série D (horas fora do contexto).
            _prev_filter   = "AND ap.bloco_id = :bloco_id" if bloco_id else "AND ap.bloco_id IS NOT NULL"
            _norm_filter   = "AND al.bloco_id = :bloco_id" if bloco_id else "AND ta.codigo = 'BLOCO'"
            _total_filter  = "AND al.bloco_id = :bloco_id" if bloco_id else "AND ta.codigo = 'BLOCO'"
            _div_cte = f"""
                ,divergente_mensal AS (
                    SELECT date_trunc('month', al.data_lancamento)::date AS mes,
                           SUM(al.minutos) AS min_div
                    FROM capacidade.agenda_lancamento al
                    WHERE al.em_uso = TRUE
                      AND al.faixa_minuto::text = 'NORMAL'
                      AND (al.bloco_id IS NULL OR al.bloco_id != :bloco_id)
                      AND al.data_lancamento IN (
                          SELECT DISTINCT ap2.data
                          FROM capacidade.agenda_prevista_admin ap2
                          WHERE ap2.em_uso = TRUE AND ap2.bloco_id = :bloco_id
                      )
                    GROUP BY 1
                )
            """ if bloco_id else ""
            _div_join  = "LEFT JOIN divergente_mensal dv ON dv.mes = m.mes" if bloco_id else ""
            _div_col   = "SUM(COALESCE(dv.min_div, 0)) OVER (ORDER BY m.mes ROWS UNBOUNDED PRECEDING) AS minutos_divergente_acum" if bloco_id else "0 AS minutos_divergente_acum"
            _norm_join = "LEFT JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id" if not bloco_id else ""
            _norm_join2 = "LEFT JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id" if not bloco_id else ""
            sql_timeline_mensal = text(f"""
                WITH meses AS (
                    SELECT generate_series(
                        date_trunc('month', CURRENT_DATE - INTERVAL '11 months')::date,
                        date_trunc('month', CURRENT_DATE)::date,
                        '1 month'::interval
                    )::date AS mes
                ),
                previsto_mensal AS (
                    SELECT date_trunc('month', ap.data)::date AS mes,
                           SUM(ap.minutos_planejados_normais + ap.minutos_planejados_extras) AS min_prev
                    FROM capacidade.agenda_prevista_admin ap
                    WHERE ap.em_uso = TRUE {_prev_filter}
                    GROUP BY 1
                ),
                lancado_normal_mensal AS (
                    SELECT date_trunc('month', al.data_lancamento)::date AS mes,
                           SUM(al.minutos) AS min_norm
                    FROM capacidade.agenda_lancamento al
                    {_norm_join}
                    WHERE al.em_uso = TRUE {_norm_filter}
                      AND al.faixa_minuto::text = 'NORMAL'
                    GROUP BY 1
                ),
                lancado_total_mensal AS (
                    SELECT date_trunc('month', al.data_lancamento)::date AS mes,
                           SUM(al.minutos) AS min_total
                    FROM capacidade.agenda_lancamento al
                    {_norm_join2}
                    WHERE al.em_uso = TRUE {_total_filter}
                    GROUP BY 1
                )
                {_div_cte}
                SELECT
                    m.mes::text AS mes,
                    SUM(COALESCE(p.min_prev,   0))
                        OVER (ORDER BY m.mes ROWS UNBOUNDED PRECEDING) AS minutos_previstos_acum,
                    SUM(COALESCE(ln.min_norm,  0))
                        OVER (ORDER BY m.mes ROWS UNBOUNDED PRECEDING) AS minutos_lancados_normal_acum,
                    SUM(COALESCE(lt.min_total, 0))
                        OVER (ORDER BY m.mes ROWS UNBOUNDED PRECEDING) AS minutos_lancados_total_acum,
                    {_div_col}
                FROM meses m
                LEFT JOIN previsto_mensal       p  ON p.mes  = m.mes
                LEFT JOIN lancado_normal_mensal ln ON ln.mes = m.mes
                LEFT JOIN lancado_total_mensal  lt ON lt.mes = m.mes
                {_div_join}
                ORDER BY m.mes
            """)
            for row in conn.execute(sql_timeline_mensal, bp):
                timeline_mensal.append(MesTrilhaResposta(
                    mes=str(row.mes),
                    minutos_previstos_acum=int(row.minutos_previstos_acum),
                    minutos_lancados_normal_acum=int(row.minutos_lancados_normal_acum),
                    minutos_lancados_total_acum=int(row.minutos_lancados_total_acum),
                    minutos_divergente_acum=int(row.minutos_divergente_acum or 0),
                ))

            # 9. Blocos destaque — progresso + top performers por bloco
            _bloco_destaque_cond = "AND b.id = :bloco_id" if bloco_id else ""
            sql_blocos_destaque = text(f"""
                WITH bloco_stats AS (
                    SELECT
                        b.id AS bloco_id,
                        b.nome AS bloco_nome,
                        p.nome AS projeto_nome,
                        l.nome AS lote_nome,
                        COUNT(ut.id) AS uts_total,
                        COUNT(ut.id) FILTER (WHERE e.concluida = TRUE) AS uts_concluidas,
                        COUNT(ut.id) FILTER (
                            WHERE e.concluida = FALSE AND e.data_inicio_fluxo IS NOT NULL
                        ) AS uts_em_andamento,
                        COUNT(ut.id) FILTER (WHERE e.data_inicio_fluxo IS NULL) AS uts_sem_inicio,
                        COALESCE(SUM(e.ut_dificuldade), 0) AS pontos_total,
                        COALESCE(SUM(
                            COALESCE(d.pontos_executor, 0) +
                            COALESCE(d.pontos_revisor,  0) +
                            COALESCE(d.pontos_corretor, 0)
                        ), 0) AS pontos_realizados
                    FROM sap_snapshot.macrocontrole_bloco b
                    JOIN sap_snapshot.macrocontrole_lote l ON l.id = b.lote_id
                    JOIN sap_snapshot.macrocontrole_projeto p ON p.id = l.projeto_id
                    JOIN sap_snapshot.macrocontrole_unidade_trabalho ut ON ut.bloco_id = b.id
                    LEFT JOIN kpi.estado_ut e ON e.ut_id = ut.id
                    LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = ut.id
                    WHERE p.status_id = 1
                    {_bloco_destaque_cond}
                    GROUP BY b.id, b.nome, p.nome, l.nome
                ),
                exec_rank AS (
                    SELECT d2.bloco_id,
                           d2.executor_id AS usuario_id,
                           COALESCE(u2.nome_guerra, u2.nome) AS nome_guerra,
                           SUM(d2.pontos_executor) AS pontos,
                           ROW_NUMBER() OVER (
                               PARTITION BY d2.bloco_id
                               ORDER BY SUM(d2.pontos_executor) DESC
                           ) AS rn
                    FROM kpi.distribuicao_pontos d2
                    JOIN sap_snapshot.dgeo_usuario u2 ON u2.id = d2.executor_id
                    WHERE d2.pontos_executor > 0
                    GROUP BY d2.bloco_id, d2.executor_id, u2.nome, u2.nome_guerra
                ),
                rev_rank AS (
                    SELECT d3.bloco_id,
                           d3.revisor_id AS usuario_id,
                           COALESCE(u3.nome_guerra, u3.nome) AS nome_guerra,
                           SUM(d3.pontos_revisor) AS pontos,
                           ROW_NUMBER() OVER (
                               PARTITION BY d3.bloco_id
                               ORDER BY SUM(d3.pontos_revisor) DESC
                           ) AS rn
                    FROM kpi.distribuicao_pontos d3
                    JOIN sap_snapshot.dgeo_usuario u3 ON u3.id = d3.revisor_id
                    WHERE d3.pontos_revisor > 0
                    GROUP BY d3.bloco_id, d3.revisor_id, u3.nome, u3.nome_guerra
                ),
                exec_agg AS (
                    SELECT bloco_id,
                           json_agg(
                               json_build_object(
                                   'usuario_id', usuario_id,
                                   'nome_guerra', nome_guerra,
                                   'pontos', pontos
                               ) ORDER BY pontos DESC
                           ) AS top_exec
                    FROM exec_rank WHERE rn <= 3
                    GROUP BY bloco_id
                ),
                rev_agg AS (
                    SELECT bloco_id,
                           json_agg(
                               json_build_object(
                                   'usuario_id', usuario_id,
                                   'nome_guerra', nome_guerra,
                                   'pontos', pontos
                               ) ORDER BY pontos DESC
                           ) AS top_rev
                    FROM rev_rank WHERE rn <= 3
                    GROUP BY bloco_id
                )
                SELECT
                    bs.*,
                    COALESCE(ea.top_exec, '[]'::json) AS top_executores,
                    COALESCE(ra.top_rev,  '[]'::json) AS top_revisores
                FROM bloco_stats bs
                LEFT JOIN exec_agg ea ON ea.bloco_id = bs.bloco_id
                LEFT JOIN rev_agg  ra ON ra.bloco_id = bs.bloco_id
                ORDER BY bs.bloco_nome
            """)

            import json as _json
            for row in conn.execute(sql_blocos_destaque, bp):
                pt = float(row.pontos_total or 0)
                pr = float(row.pontos_realizados or 0)
                prog = round(pr / pt * 100, 2) if pt > 0 else None

                raw_exec = row.top_executores
                raw_rev  = row.top_revisores
                if isinstance(raw_exec, str):
                    raw_exec = _json.loads(raw_exec)
                if isinstance(raw_rev, str):
                    raw_rev = _json.loads(raw_rev)

                def _to_contrib(items: list, total: float) -> list[ContribuidorBloco]:
                    out = []
                    for it in (items or []):
                        pts = float(it.get("pontos") or 0)
                        out.append(ContribuidorBloco(
                            usuario_id=int(it.get("usuario_id") or 0),
                            nome_guerra=str(it.get("nome_guerra") or ""),
                            pontos=pts,
                            percentual=round(pts / total * 100, 1) if total > 0 else 0.0,
                        ))
                    return out

                blocos_destaque.append(BlocoDestaque(
                    bloco_id=row.bloco_id,
                    bloco_nome=row.bloco_nome,
                    projeto_nome=row.projeto_nome,
                    lote_nome=row.lote_nome,
                    uts_total=int(row.uts_total or 0),
                    uts_concluidas=int(row.uts_concluidas or 0),
                    uts_em_andamento=int(row.uts_em_andamento or 0),
                    uts_sem_inicio=int(row.uts_sem_inicio or 0),
                    pontos_total=pt,
                    pontos_realizados=pr,
                    progresso=prog,
                    top_executores=_to_contrib(raw_exec, pt),
                    top_revisores=_to_contrib(raw_rev, pt),
                ))

            # 10. Alertas — UTs concluídas sem nota ou com nota inválida
            sql_alertas = text(f"""
                SELECT
                    e.ut_id,
                    b.nome                       AS bloco_nome,
                    l.nome                       AS lote_nome,
                    e.subfase_nome,
                    f.exec_usuario_id            AS executor_id,
                    e.usuario_executor_nome      AS nome_executor,
                    f.rev_usuario_id             AS revisor_id,
                    e.usuario_revisor_nome       AS nome_revisor,
                    f.cor_atividade_id,
                    e.ocorrencia
                FROM kpi.estado_ut e
                JOIN sap_snapshot.macrocontrole_unidade_trabalho ut
                    ON ut.id = e.ut_id
                JOIN sap_snapshot.macrocontrole_bloco b ON b.id = ut.bloco_id
                JOIN sap_snapshot.macrocontrole_lote  l ON l.id = b.lote_id
                LEFT JOIN kpi.fluxo_ut f ON f.ut_id = e.ut_id
                WHERE e.concluida = TRUE
                  AND e.ocorrencia IN ('NOTA_AUSENTE', 'NOTA_INVALIDA')
                  {bloco_cond_e}
                ORDER BY b.nome, e.subfase_nome, e.ut_id
                LIMIT 500
            """)
            for row in conn.execute(sql_alertas, bp):
                alertas_nota.append(AlertaNotaAusente(
                    ut_id=int(row.ut_id),
                    bloco_nome=str(row.bloco_nome or ""),
                    lote_nome=str(row.lote_nome or ""),
                    subfase_nome=str(row.subfase_nome or ""),
                    executor_id=row.executor_id,
                    nome_executor=row.nome_executor,
                    revisor_id=row.revisor_id,
                    nome_revisor=row.nome_revisor,
                    cor_atividade_id=row.cor_atividade_id,
                    ocorrencia=str(row.ocorrencia or ""),
                ))

            # 10.5 Lista de subfases disponíveis para selector do ranking
            # Inclui bloco_id/bloco_nome para contextualizar quando nenhum bloco está filtrado
            _bloco_sf_cond = "AND e.bloco_id = :bloco_id" if bloco_id else ""
            sql_subfases = text(f"""
                SELECT DISTINCT e.subfase_id, e.subfase_nome,
                                e.bloco_id,   e.bloco_nome
                FROM kpi.estado_ut e
                WHERE e.subfase_id IS NOT NULL
                  {_bloco_sf_cond}
                ORDER BY e.bloco_nome, e.subfase_nome
            """)
            for row in conn.execute(sql_subfases, bp):
                subfases_disponiveis.append({
                    "subfase_id": int(row.subfase_id),
                    "subfase_nome": str(row.subfase_nome or ""),
                    "bloco_id":    int(row.bloco_id) if row.bloco_id else None,
                    "bloco_nome":  str(row.bloco_nome or "") if row.bloco_nome else None,
                })
                if subfase_id and int(row.subfase_id) == subfase_id:
                    subfase_filtro_nome = str(row.subfase_nome or "")

            # 11. Ranking global de operadores
            # Filtro de subfase via JOIN em estado_ut (independente de distribuicao_pontos.subfase_id)
            _bloco_rank_cond = "AND d.bloco_id = :bloco_id" if bloco_id else ""
            _subfase_rank_join = (
                "JOIN kpi.estado_ut esf ON esf.ut_id = d.ut_id AND esf.subfase_id = :subfase_id"
                if subfase_id else ""
            )
            sql_ranking = text(f"""
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY
                            COALESCE(SUM(d.pontos_executor), 0) +
                            COALESCE(SUM(d.pontos_revisor),  0) +
                            COALESCE(SUM(d.pontos_corretor), 0) DESC
                    ) AS posicao,
                    u.id AS usuario_id,
                    COALESCE(u.nome_guerra, u.nome) AS nome_guerra,
                    COALESCE(SUM(d.pontos_executor), 0)  AS pontos_executor,
                    COALESCE(SUM(d.pontos_revisor),  0)  AS pontos_revisor,
                    COALESCE(SUM(d.pontos_corretor), 0)  AS pontos_corretor,
                    COALESCE(SUM(d.pontos_executor), 0) +
                    COALESCE(SUM(d.pontos_revisor),  0) +
                    COALESCE(SUM(d.pontos_corretor), 0)  AS pontos_total,
                    COUNT(DISTINCT CASE
                        WHEN d.executor_id = u.id AND d.pontos_executor > 0 THEN d.ut_id
                    END) AS uts_executadas,
                    COUNT(DISTINCT CASE
                        WHEN d.revisor_id  = u.id AND d.pontos_revisor  > 0 THEN d.ut_id
                    END) AS uts_revisadas
                FROM sap_snapshot.dgeo_usuario u
                JOIN kpi.distribuicao_pontos d
                    ON (d.executor_id = u.id
                    OR  d.revisor_id  = u.id
                    OR  d.corretor_id = u.id)
                    {_bloco_rank_cond}
                {_subfase_rank_join}
                GROUP BY u.id, u.nome, u.nome_guerra
                HAVING
                    COALESCE(SUM(d.pontos_executor), 0) +
                    COALESCE(SUM(d.pontos_revisor),  0) +
                    COALESCE(SUM(d.pontos_corretor), 0) > 0
                ORDER BY pontos_total DESC
                LIMIT 50
            """)
            for row in conn.execute(sql_ranking, bp_rank):
                ranking_operadores.append(RankingOperador(
                    posicao=int(row.posicao),
                    usuario_id=int(row.usuario_id),
                    nome_guerra=str(row.nome_guerra or ""),
                    pontos_executor=float(row.pontos_executor or 0),
                    pontos_revisor=float(row.pontos_revisor or 0),
                    pontos_corretor=float(row.pontos_corretor or 0),
                    pontos_total=float(row.pontos_total or 0),
                    uts_executadas=int(row.uts_executadas or 0),
                    uts_revisadas=int(row.uts_revisadas or 0),
                ))

            # 12. Velocidade semanal — UTs concluídas nas últimas 8 semanas
            sql_velocidade = text(f"""
                WITH semanas AS (
                    SELECT generate_series(
                        date_trunc('week', CURRENT_DATE) - INTERVAL '7 weeks',
                        date_trunc('week', CURRENT_DATE),
                        '1 week'::interval
                    )::date AS semana_inicio
                ),
                uts_sem AS (
                    SELECT
                        date_trunc('week', e.data_fim_fluxo)::date AS semana,
                        COUNT(*) AS uts_concluidas,
                        COALESCE(SUM(
                            COALESCE(d.pontos_executor, 0) +
                            COALESCE(d.pontos_revisor,  0) +
                            COALESCE(d.pontos_corretor, 0)
                        ), 0) AS pontos
                    FROM kpi.estado_ut e
                    LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = e.ut_id
                    WHERE e.concluida = TRUE
                      AND e.data_fim_fluxo IS NOT NULL
                      AND e.data_fim_fluxo >=
                          date_trunc('week', CURRENT_DATE) - INTERVAL '7 weeks'
                      {bloco_cond_e}
                    GROUP BY 1
                )
                SELECT
                    to_char(s.semana_inicio, 'DD/MM')  AS semana_label,
                    s.semana_inicio::text              AS semana_inicio,
                    COALESCE(u.uts_concluidas, 0)      AS uts_concluidas,
                    COALESCE(u.pontos, 0)              AS pontos_realizados
                FROM semanas s
                LEFT JOIN uts_sem u ON u.semana = s.semana_inicio
                ORDER BY s.semana_inicio
            """)
            for row in conn.execute(sql_velocidade, bp):
                velocidade_semanal.append(SemanaVelocidade(
                    semana_label=str(row.semana_label),
                    semana_inicio=str(row.semana_inicio),
                    uts_concluidas=int(row.uts_concluidas or 0),
                    pontos_realizados=float(row.pontos_realizados or 0),
                ))

            # 13. Distribuição por ciclo
            _bloco_ciclo_cond = "WHERE e2.bloco_id = :bloco_id" if bloco_id else ""
            _bloco_ciclo_cond2 = "WHERE e3.bloco_id = :bloco_id" if bloco_id else ""
            sql_ciclos = text(f"""
                WITH totais AS (
                    SELECT COUNT(*) AS total
                    FROM kpi.estado_ut e2
                    {_bloco_ciclo_cond}
                )
                SELECT
                    COALESCE(e3.ciclo_modelo, 'DESCONHECIDO') AS ciclo,
                    COUNT(*) AS quantidade,
                    ROUND(COUNT(*) * 100.0 / NULLIF(t.total, 0), 1) AS percentual
                FROM kpi.estado_ut e3, totais t
                {_bloco_ciclo_cond2}
                GROUP BY e3.ciclo_modelo, t.total
                ORDER BY quantidade DESC
            """)
            for row in conn.execute(sql_ciclos, bp):
                distribuicao_ciclos.append(DistribuicaoCiclo(
                    ciclo=str(row.ciclo or ""),
                    quantidade=int(row.quantidade or 0),
                    percentual=float(row.percentual or 0),
                ))

    except Exception:
        _logger.exception("Erro ao calcular kpi_dashboard bloco_id=%s subfase_id=%s", bloco_id, subfase_id)
        raise HTTPException(status_code=500, detail="Erro ao calcular dashboard KPI")

    progresso_geral = (pontos_realizados / pontos_totais * 100) if pontos_totais > 0 else None
    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=30"
    return DashboardResponse(
        sap_snapshot_atualizado_em=snapshot_ts,
        kpi_calculado_em=kpi_ts,
        projetos_ativos=projetos_ativos,
        blocos_sap_cadastrados=blocos_sap_cadastrados,
        progresso_geral=round(progresso_geral, 2) if progresso_geral is not None else None,
        pontos_totais=pontos_totais,
        pontos_realizados=pontos_realizados,
        horas_previstas_producao_min=horas_previstas_producao_min,
        horas_lancadas_producao_min=horas_lancadas_producao_min,
        hierarquia=hierarquia,
        top_executor=top_executor,
        top_revisor=top_revisor,
        top_executores_subfase=top_executores_subfase,
        top_revisores_subfase=top_revisores_subfase,
        timeline_mensal=timeline_mensal,
        blocos_destaque=blocos_destaque,
        alertas_nota=alertas_nota,
        ranking_operadores=ranking_operadores,
        velocidade_semanal=velocidade_semanal,
        distribuicao_ciclos=distribuicao_ciclos,
        bloco_filtro_id=bloco_id,
        bloco_filtro_nome=bloco_filtro_nome,
        subfase_filtro_id=subfase_id,
        subfase_filtro_nome=subfase_filtro_nome,
        subfases_disponiveis=subfases_disponiveis,
    )


# ---------------------------------------------------------------------------
# Timeline diária — admin (granularidade por dia dentro de um mês)
# ---------------------------------------------------------------------------

@router.get("/timeline-diario", summary="Timeline diária de horas produzidas em um mês")
def kpi_timeline_diario(
    _: UsuarioLogado,
    request: Request,
    response: Response,
    mes: str = Query(..., description="Mês no formato YYYY-MM"),
    bloco_id: int | None = Query(None),
) -> list[MesTrilhaResposta]:
    """Retorna a evolução acumulada de horas dia-a-dia para um mês específico.

    Usa o mesmo modelo MesTrilhaResposta com o campo `mes` contendo a data no
    formato YYYY-MM-DD (um ponto por dia do mês).
    """
    engine_cp = request.app.state.engine_cp
    result: list[MesTrilhaResposta] = []

    # Calcular os limites do mês em Python para evitar cast `:param::date` que
    # psycopg2 não suporta na sintaxe de named params do SQLAlchemy text()
    from datetime import date as _date
    ano, mm = int(mes[:4]), int(mes[5:7])
    dia_ini = _date(ano, mm, 1)
    if mm == 12:
        dia_fim = _date(ano + 1, 1, 1)
    else:
        dia_fim = _date(ano, mm + 1, 1)

    # Mesmos filtros do gráfico anual para garantir consistência:
    # — sem bloco_id: apenas agenda de bloco produtivo (bloco_id IS NOT NULL, ta.codigo='BLOCO')
    # — com bloco_id: filtra pelo bloco específico
    if bloco_id:
        _prev_cond   = "AND ap.bloco_id = :bloco_id"
        _norm_join   = ""
        _norm_cond   = "AND al.bloco_id = :bloco_id"
        _total_join  = ""
        _total_cond  = "AND al.bloco_id = :bloco_id"
    else:
        _prev_cond   = "AND ap.bloco_id IS NOT NULL"
        _norm_join   = "LEFT JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id"
        _norm_cond   = "AND ta.codigo = 'BLOCO'"
        _total_join  = "LEFT JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id"
        _total_cond  = "AND ta.codigo = 'BLOCO'"

    bp: dict = {"dia_ini": dia_ini, "dia_fim": dia_fim}
    if bloco_id:
        bp["bloco_id"] = bloco_id

    sql = text(f"""
        WITH dias AS (
            SELECT generate_series(:dia_ini, :dia_fim - INTERVAL '1 day', '1 day'::interval)::date AS dia
        ),
        previsto AS (
            SELECT ap.data AS dia,
                   SUM(ap.minutos_planejados_normais + ap.minutos_planejados_extras) AS min_prev
            FROM capacidade.agenda_prevista_admin ap
            WHERE ap.em_uso = TRUE
              AND ap.data >= :dia_ini
              AND ap.data <  :dia_fim
              {_prev_cond}
            GROUP BY 1
        ),
        lancado_normal AS (
            SELECT al.data_lancamento AS dia,
                   SUM(al.minutos)    AS min_norm
            FROM capacidade.agenda_lancamento al
            {_norm_join}
            WHERE al.em_uso = TRUE
              AND al.faixa_minuto::text = 'NORMAL'
              AND al.data_lancamento >= :dia_ini
              AND al.data_lancamento <  :dia_fim
              {_norm_cond}
            GROUP BY 1
        ),
        lancado_total AS (
            SELECT al.data_lancamento AS dia,
                   SUM(al.minutos)    AS min_total
            FROM capacidade.agenda_lancamento al
            {_total_join}
            WHERE al.em_uso = TRUE
              AND al.data_lancamento >= :dia_ini
              AND al.data_lancamento <  :dia_fim
              {_total_cond}
            GROUP BY 1
        )
        SELECT
            d.dia::text AS mes,
            SUM(COALESCE(p.min_prev,   0)) OVER (ORDER BY d.dia ROWS UNBOUNDED PRECEDING) AS minutos_previstos_acum,
            SUM(COALESCE(ln.min_norm,  0)) OVER (ORDER BY d.dia ROWS UNBOUNDED PRECEDING) AS minutos_lancados_normal_acum,
            SUM(COALESCE(lt.min_total, 0)) OVER (ORDER BY d.dia ROWS UNBOUNDED PRECEDING) AS minutos_lancados_total_acum,
            0 AS minutos_divergente_acum
        FROM dias d
        LEFT JOIN previsto       p  ON p.dia  = d.dia
        LEFT JOIN lancado_normal ln ON ln.dia  = d.dia
        LEFT JOIN lancado_total  lt ON lt.dia  = d.dia
        ORDER BY d.dia
    """)

    try:
        with engine_cp.connect() as conn:
            for row in conn.execute(sql, bp):
                result.append(MesTrilhaResposta(
                    mes=str(row.mes),
                    minutos_previstos_acum=int(row.minutos_previstos_acum or 0),
                    minutos_lancados_normal_acum=int(row.minutos_lancados_normal_acum or 0),
                    minutos_lancados_total_acum=int(row.minutos_lancados_total_acum or 0),
                    minutos_divergente_acum=0,
                ))
    except Exception:
        _logger.exception("Erro ao calcular timeline diária mes=%s bloco_id=%s", mes, bloco_id)
        raise HTTPException(status_code=500, detail="Erro ao calcular timeline diária")

    response.headers["Cache-Control"] = "private, max-age=300, stale-while-revalidate=60"
    return result


# ---------------------------------------------------------------------------
# Modelos — Dashboard do usuário (operador)
# ---------------------------------------------------------------------------

class PontosSubfaseResposta(BaseModel):
    subfase_id: int
    subfase_nome: str
    pontos: float                      # pontos do usuário nesta subfase/papel
    pontos_total_subfase: float = 0.0  # total alocado na subfase/bloco (kpi.fluxo_ut)


class BlocoDetalheUsuario(BaseModel):
    bloco_id: int
    bloco_nome: str
    projeto_nome: str
    pontos_total_bloco: float          # total distribuído a todos os usuários (kpi.distribuicao_pontos)
    pontos_usuario_bloco: float        # contribuição do usuário
    pontos_alocados_bloco: float = 0.0 # total alocado no bloco (kpi.fluxo_ut) — base 100%
    como_executor: list[PontosSubfaseResposta]
    como_revisor: list[PontosSubfaseResposta]
    como_corretor: list[PontosSubfaseResposta]


class DiaHorasResposta(BaseModel):
    data: str
    minutos_previstos: int
    minutos_lancados: int
    minutos_lancados_normal: int = 0


class PizzaFatia(BaseModel):
    nome: str
    cor: str
    minutos: int
    percentual: float


class PizzaDistribuicaoResponse(BaseModel):
    mes: str
    total_capacidade_min: int
    nao_alocado_min: int
    fatias: list[PizzaFatia]


class MeuDashboardResposta(BaseModel):
    sap_snapshot_atualizado_em: str | None
    kpi_calculado_em: str | None
    blocos: list[BlocoDetalheUsuario]
    pontos_total_geral: float
    pontos_usuario_geral: float
    horas_previstas_producao_min: int
    horas_lancadas_producao_min: int
    horas_lancadas_externas_min: int
    timeline: list[DiaHorasResposta]
    timeline_mensal: list[MesTrilhaResposta] = []


# ---------------------------------------------------------------------------
# Rota /kpi/meu-dashboard
# ---------------------------------------------------------------------------


@router.get("/meu-dashboard", summary="Dashboard do usuário autenticado")
def meu_dashboard(usuario: UsuarioLogado, request: Request, response: Response) -> MeuDashboardResposta:
    """Retorna KPI personalizado para o usuário logado.

    Inclui:
    - Blocos vinculados ao usuário (como executor, revisor ou corretor)
    - Pontos por bloco e subfase por cada papel
    - Horas previstas e lançadas em produção e externamente
    - Timeline diária dos últimos 45 dias (minutos previstos × realizados)
    """
    engine_cp = request.app.state.engine_cp
    uid = usuario.usuario_id
    snapshot_ts, kpi_ts = _get_sync_timestamps(engine_cp)

    blocos_map: dict[int, BlocoDetalheUsuario] = {}
    horas_previstas = 0
    horas_lancadas_prod = 0
    horas_lancadas_ext = 0
    timeline: list[DiaHorasResposta] = []
    timeline_mensal: list[MesTrilhaResposta] = []

    try:
        with engine_cp.connect() as conn:
            # ── 1. Pontos por bloco/subfase por papel ─────────────────────
            # kpi.distribuicao_pontos tem ut_id mas não subfase_id diretamente.
            # kpi.estado_ut NÃO possui subfase_id — apenas subfase_nome (text).
            # A forma correta é ir via sap_snapshot.macrocontrole_unidade_trabalho
            # que possui subfase_id como FK, da mesma forma que _CTE_UT_BASE faz.
            sql_pontos = text("""
                WITH user_pontos AS (
                    SELECT
                        b.id                AS bloco_id,
                        b.nome              AS bloco_nome,
                        p.nome              AS projeto_nome,
                        sf.id               AS subfase_id,
                        sf.nome             AS subfase_nome,
                        COALESCE(SUM(CASE WHEN d.executor_id = :uid AND d.pontos_executor > 0
                                          THEN d.pontos_executor ELSE 0 END), 0) AS pontos_executor,
                        COALESCE(SUM(CASE WHEN d.revisor_id  = :uid AND d.pontos_revisor  > 0
                                          THEN d.pontos_revisor  ELSE 0 END), 0) AS pontos_revisor,
                        COALESCE(SUM(CASE WHEN d.corretor_id = :uid AND d.pontos_corretor > 0
                                          THEN d.pontos_corretor ELSE 0 END), 0) AS pontos_corretor,
                        COALESCE(SUM(d.pontos_executor + d.pontos_revisor + d.pontos_corretor), 0)
                            AS pontos_total_subfase
                    FROM kpi.distribuicao_pontos d
                    JOIN sap_snapshot.macrocontrole_unidade_trabalho ut
                        ON ut.id = d.ut_id
                    JOIN sap_snapshot.macrocontrole_subfase sf
                        ON sf.id = ut.subfase_id
                    JOIN sap_snapshot.macrocontrole_bloco b
                        ON b.id = ut.bloco_id
                    JOIN sap_snapshot.macrocontrole_lote l
                        ON l.id = b.lote_id
                    JOIN sap_snapshot.macrocontrole_projeto p
                        ON p.id = l.projeto_id
                    WHERE (d.executor_id = :uid OR d.revisor_id = :uid OR d.corretor_id = :uid)
                    GROUP BY b.id, b.nome, p.nome, sf.id, sf.nome
                )
                SELECT *
                FROM user_pontos
                WHERE pontos_executor > 0 OR pontos_revisor > 0 OR pontos_corretor > 0
                ORDER BY bloco_nome, subfase_nome
            """)

            for row in conn.execute(sql_pontos, {"uid": uid}):
                bloco_id = row.bloco_id

                if bloco_id not in blocos_map:
                    # Busca o total de pontos do bloco (todos os usuários) na 1ª vez
                    sql_total = text("""
                        SELECT COALESCE(SUM(d.pontos_executor + d.pontos_revisor + d.pontos_corretor), 0)
                        FROM kpi.distribuicao_pontos d
                        JOIN sap_snapshot.macrocontrole_unidade_trabalho ut ON ut.id = d.ut_id
                        WHERE ut.bloco_id = :bloco_id
                    """)
                    total_res = conn.execute(sql_total, {"bloco_id": bloco_id}).scalar() or 0.0

                    blocos_map[bloco_id] = BlocoDetalheUsuario(
                        bloco_id=bloco_id,
                        bloco_nome=row.bloco_nome,
                        projeto_nome=row.projeto_nome,
                        pontos_total_bloco=float(total_res),
                        pontos_usuario_bloco=0.0,
                        como_executor=[],
                        como_revisor=[],
                        como_corretor=[],
                    )

                bloco = blocos_map[bloco_id]
                pts_exec = float(row.pontos_executor)
                pts_rev  = float(row.pontos_revisor)
                pts_cor  = float(row.pontos_corretor)
                subfase  = row.subfase_nome
                sf_id    = row.subfase_id

                bloco.pontos_usuario_bloco += pts_exec + pts_rev + pts_cor

                if pts_exec > 0:
                    bloco.como_executor.append(PontosSubfaseResposta(
                        subfase_id=sf_id, subfase_nome=subfase, pontos=pts_exec,
                    ))
                if pts_rev > 0:
                    bloco.como_revisor.append(PontosSubfaseResposta(
                        subfase_id=sf_id, subfase_nome=subfase, pontos=pts_rev,
                    ))
                if pts_cor > 0:
                    bloco.como_corretor.append(PontosSubfaseResposta(
                        subfase_id=sf_id, subfase_nome=subfase, pontos=pts_cor,
                    ))

            # Sort subfases por pontos desc em cada papel
            for bloco in blocos_map.values():
                bloco.como_executor.sort(key=lambda x: x.pontos, reverse=True)
                bloco.como_revisor.sort(key=lambda x: x.pontos, reverse=True)
                bloco.como_corretor.sort(key=lambda x: x.pontos, reverse=True)

            # ── 1b. Totais alocados por bloco/subfase (kpi.fluxo_ut) ──────
            # Usa bloco_nome para JOIN pois fluxo_ut não expõe bloco_id diretamente.
            if blocos_map:
                _ids_str = ",".join(str(bid) for bid in blocos_map)
                sql_sf_totais = text(f"""
                    SELECT
                        b.id                                        AS bloco_id,
                        f.subfase_id,
                        SUM(COALESCE(f.ut_dificuldade, 0))          AS pontos_alocados
                    FROM kpi.fluxo_ut f
                    JOIN sap_snapshot.macrocontrole_bloco b
                        ON b.nome = f.bloco_nome
                    WHERE b.id IN ({_ids_str})
                    GROUP BY b.id, f.subfase_id
                """)
                sf_totais: dict[tuple[int, int], float] = {}
                bloco_alocados: dict[int, float] = {}
                for row in conn.execute(sql_sf_totais):
                    bid = int(row.bloco_id)
                    pts = float(row.pontos_alocados)
                    sf_totais[(bid, int(row.subfase_id))] = pts
                    bloco_alocados[bid] = bloco_alocados.get(bid, 0.0) + pts

                for bid, bloco in blocos_map.items():
                    bloco.pontos_alocados_bloco = bloco_alocados.get(bid, bloco.pontos_total_bloco)
                    for sf in bloco.como_executor + bloco.como_revisor + bloco.como_corretor:
                        sf.pontos_total_subfase = sf_totais.get(
                            (bid, sf.subfase_id), sf.pontos
                        )

            # ── 2. Horas previstas em produção (todos os tempos) ──────────
            sql_prev = text("""
                SELECT COALESCE(SUM(ap.minutos_planejados_normais + ap.minutos_planejados_extras), 0)
                FROM capacidade.agenda_prevista_admin ap
                WHERE ap.usuario_id = :uid
                  AND ap.em_uso = TRUE
                  AND ap.bloco_id IS NOT NULL
            """)
            horas_previstas = int(conn.execute(sql_prev, {"uid": uid}).scalar() or 0)

            # ── 3. Horas lançadas em produção ─────────────────────────────
            sql_lanc_prod = text("""
                SELECT COALESCE(SUM(al.minutos), 0)
                FROM capacidade.agenda_lancamento al
                JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id
                WHERE al.usuario_id = :uid
                  AND al.em_uso = TRUE
                  AND ta.codigo = 'BLOCO'
            """)
            horas_lancadas_prod = int(conn.execute(sql_lanc_prod, {"uid": uid}).scalar() or 0)

            # ── 4. Horas lançadas fora da produção ────────────────────────
            sql_lanc_ext = text("""
                SELECT COALESCE(SUM(al.minutos), 0)
                FROM capacidade.agenda_lancamento al
                JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id
                WHERE al.usuario_id = :uid
                  AND al.em_uso = TRUE
                  AND ta.codigo != 'BLOCO'
            """)
            horas_lancadas_ext = int(conn.execute(sql_lanc_ext, {"uid": uid}).scalar() or 0)

            # ── 5. Timeline (últimos 45 dias) ─────────────────────────────
            sql_timeline = text("""
                WITH dias AS (
                    SELECT generate_series(
                        CURRENT_DATE - INTERVAL '44 days',
                        CURRENT_DATE,
                        '1 day'::interval
                    )::date AS data
                ),
                previstos AS (
                    SELECT ap.data,
                           SUM(ap.minutos_planejados_normais + ap.minutos_planejados_extras) AS minutos
                    FROM capacidade.agenda_prevista_admin ap
                    WHERE ap.usuario_id = :uid
                      AND ap.em_uso = TRUE
                      AND ap.bloco_id IS NOT NULL
                      AND ap.data >= CURRENT_DATE - INTERVAL '44 days'
                    GROUP BY ap.data
                ),
                lancados AS (
                    SELECT al.data_lancamento AS data,
                           SUM(al.minutos) AS minutos,
                           SUM(CASE WHEN al.faixa_minuto::text = 'NORMAL'
                                    THEN al.minutos ELSE 0 END) AS minutos_normal
                    FROM capacidade.agenda_lancamento al
                    JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id
                    WHERE al.usuario_id = :uid
                      AND al.em_uso = TRUE
                      AND ta.codigo = 'BLOCO'
                      AND al.data_lancamento >= CURRENT_DATE - INTERVAL '44 days'
                    GROUP BY al.data_lancamento
                )
                SELECT
                    d.data::text,
                    COALESCE(p.minutos, 0) AS minutos_previstos,
                    COALESCE(l.minutos, 0) AS minutos_lancados,
                    COALESCE(l.minutos_normal, 0) AS minutos_lancados_normal
                FROM dias d
                LEFT JOIN previstos p ON p.data = d.data
                LEFT JOIN lancados  l ON l.data = d.data
                ORDER BY d.data
            """)
            for row in conn.execute(sql_timeline, {"uid": uid}):
                timeline.append(DiaHorasResposta(
                    data=str(row.data),
                    minutos_previstos=int(row.minutos_previstos),
                    minutos_lancados=int(row.minutos_lancados),
                    minutos_lancados_normal=int(row.minutos_lancados_normal),
                ))

            # ── 6. Timeline mensal acumulada ──────────────────────────────
            # J: previsto, K: normal, P: normal + extra
            sql_timeline_mensal = text("""
                WITH data_inicio AS (
                    SELECT LEAST(
                        COALESCE(
                            (SELECT MIN(ap.data)
                             FROM capacidade.agenda_prevista_admin ap
                             WHERE ap.usuario_id = :uid AND ap.em_uso = TRUE
                               AND ap.bloco_id IS NOT NULL),
                            date_trunc('month', CURRENT_DATE)::date
                        ),
                        COALESCE(
                            (SELECT MIN(al.data_lancamento)
                             FROM capacidade.agenda_lancamento al
                             JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id
                             WHERE al.usuario_id = :uid AND al.em_uso = TRUE
                               AND ta.codigo = 'BLOCO'),
                            date_trunc('month', CURRENT_DATE)::date
                        )
                    ) AS inicio
                ),
                meses AS (
                    SELECT generate_series(
                        date_trunc('month', (SELECT inicio FROM data_inicio)),
                        date_trunc('month', CURRENT_DATE),
                        '1 month'::interval
                    )::date AS mes
                ),
                previsto_mensal AS (
                    SELECT date_trunc('month', ap.data)::date AS mes,
                           SUM(ap.minutos_planejados_normais + ap.minutos_planejados_extras) AS min_prev
                    FROM capacidade.agenda_prevista_admin ap
                    WHERE ap.usuario_id = :uid AND ap.em_uso = TRUE AND ap.bloco_id IS NOT NULL
                    GROUP BY 1
                ),
                lancado_normal_mensal AS (
                    SELECT date_trunc('month', al.data_lancamento)::date AS mes,
                           SUM(al.minutos) AS min_norm
                    FROM capacidade.agenda_lancamento al
                    JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id
                    WHERE al.usuario_id = :uid AND al.em_uso = TRUE AND ta.codigo = 'BLOCO'
                      AND al.faixa_minuto::text = 'NORMAL'
                    GROUP BY 1
                ),
                lancado_total_mensal AS (
                    SELECT date_trunc('month', al.data_lancamento)::date AS mes,
                           SUM(al.minutos) AS min_total
                    FROM capacidade.agenda_lancamento al
                    JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id
                    WHERE al.usuario_id = :uid AND al.em_uso = TRUE AND ta.codigo = 'BLOCO'
                    GROUP BY 1
                )
                SELECT
                    m.mes::text AS mes,
                    SUM(COALESCE(p.min_prev,   0))
                        OVER (ORDER BY m.mes ROWS UNBOUNDED PRECEDING) AS minutos_previstos_acum,
                    SUM(COALESCE(ln.min_norm,  0))
                        OVER (ORDER BY m.mes ROWS UNBOUNDED PRECEDING) AS minutos_lancados_normal_acum,
                    SUM(COALESCE(lt.min_total, 0))
                        OVER (ORDER BY m.mes ROWS UNBOUNDED PRECEDING) AS minutos_lancados_total_acum
                FROM meses m
                LEFT JOIN previsto_mensal       p  ON p.mes  = m.mes
                LEFT JOIN lancado_normal_mensal ln ON ln.mes = m.mes
                LEFT JOIN lancado_total_mensal  lt ON lt.mes = m.mes
                ORDER BY m.mes
            """)
            for row in conn.execute(sql_timeline_mensal, {"uid": uid}):
                timeline_mensal.append(MesTrilhaResposta(
                    mes=str(row.mes),
                    minutos_previstos_acum=int(row.minutos_previstos_acum),
                    minutos_lancados_normal_acum=int(row.minutos_lancados_normal_acum),
                    minutos_lancados_total_acum=int(row.minutos_lancados_total_acum),
                ))
    except Exception:
        _logger.exception("Erro ao calcular meu-dashboard para usuario_id=%s", uid)
        raise HTTPException(status_code=500, detail="Erro ao calcular seu dashboard")

    blocos_list = sorted(blocos_map.values(), key=lambda b: b.bloco_nome)
    pontos_total_geral   = sum(b.pontos_total_bloco   for b in blocos_list)
    pontos_usuario_geral = sum(b.pontos_usuario_bloco for b in blocos_list)

    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=30"
    return MeuDashboardResposta(
        sap_snapshot_atualizado_em=snapshot_ts,
        kpi_calculado_em=kpi_ts,
        blocos=blocos_list,
        pontos_total_geral=pontos_total_geral,
        pontos_usuario_geral=pontos_usuario_geral,
        horas_previstas_producao_min=horas_previstas,
        horas_lancadas_producao_min=horas_lancadas_prod,
        horas_lancadas_externas_min=horas_lancadas_ext,
        timeline=timeline,
        timeline_mensal=timeline_mensal,
    )


# ---------------------------------------------------------------------------
# Helper — parse mes string para date
# ---------------------------------------------------------------------------

def _parse_mes(mes: str) -> date:
    """Converte 'YYYY-MM' para o 1º dia do mês. Default: mês atual."""
    if mes:
        try:
            ano, m = mes.split("-")
            return date(int(ano), int(m), 1)
        except Exception:
            _logger.debug("Formato de mês inválido '%s', usando mês atual", mes)
    today = date.today()
    return today.replace(day=1)


def _dias_uteis_do_mes(mes_inicio: date) -> int:
    """Retorna a quantidade de dias úteis (seg–sex) no mês, sem contar feriados.

    Usado como fallback quando o usuário não tem capacidade_dia cadastrada —
    garante que o gráfico de pizza exiba 100% não alocado em vez de ficar em branco.
    """
    ano, mes = mes_inicio.year, mes_inicio.month
    _, ultimo = calendar.monthrange(ano, mes)
    return sum(1 for d in range(1, ultimo + 1) if date(ano, mes, d).weekday() < 5)


def _pizza_query(
    engine_cp: Any,
    mes_inicio: date,
    usuario_id: int | None,
) -> PizzaDistribuicaoResponse:
    """Calcula a distribuição de lançamentos para um mês, opcionalmente filtrado por usuário.

    A base de cálculo é sempre a capacidade normal disponível nos dias úteis.
    Quando nenhum lançamento existe, exibe 100% como "Não alocado".
    Quando usuario_id é None (todos), considera apenas usuários ativos (sap_snapshot.dgeo_usuario.ativo).
    """
    mes_str = mes_inicio.strftime("%Y-%m-%d")

    if usuario_id:
        # Filtro por usuário específico — usa uid diretamente
        fatia_user_join   = ""
        fatia_user_filter = "AND al.usuario_id = :uid"
        cap_user_join     = ""
        cap_user_filter   = "AND cd.usuario_id = :uid"
    else:
        # Todos os usuários ativos
        fatia_user_join   = "JOIN sap_snapshot.dgeo_usuario u ON u.id = al.usuario_id AND u.ativo = TRUE"
        fatia_user_filter = ""
        cap_user_join     = "JOIN sap_snapshot.dgeo_usuario u ON u.id = cd.usuario_id AND u.ativo = TRUE"
        cap_user_filter   = ""

    sql_fatias = text(f"""
        SELECT
            ta.nome AS nome,
            ta.cor  AS cor,
            SUM(al.minutos) AS minutos
        FROM capacidade.agenda_lancamento al
        JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id
        {fatia_user_join}
        WHERE al.em_uso = TRUE
          AND al.faixa_minuto::text = 'NORMAL'
          AND date_trunc('month', al.data_lancamento)::date = :mes_inicio
          {fatia_user_filter}
        GROUP BY ta.nome, ta.cor
        ORDER BY minutos DESC
    """)

    # Capacidade: apenas dias úteis (eh_dia_util = TRUE), usuários ativos
    sql_capacidade = text(f"""
        SELECT COALESCE(SUM(cd.minutos_capacidade_normal_prevista), 0) AS total
        FROM capacidade.capacidade_dia cd
        {cap_user_join}
        WHERE date_trunc('month', cd.data)::date = :mes_inicio
          AND cd.eh_dia_util = TRUE
          {cap_user_filter}
    """)

    params: dict[str, Any] = {"mes_inicio": mes_str}
    if usuario_id:
        params["uid"] = usuario_id

    fatias_raw: list[dict[str, Any]] = []
    total_lancado = 0
    total_capacidade = 0

    try:
        with engine_cp.connect() as conn:
            for row in conn.execute(sql_fatias, params):
                fatias_raw.append({
                    "nome": row.nome,
                    "cor": row.cor or "#5B8DEE",
                    "minutos": int(row.minutos),
                })
                total_lancado += int(row.minutos)

            row_cap = conn.execute(sql_capacidade, params).fetchone()
            total_capacidade = int(row_cap.total) if row_cap else 0
    except Exception:
        _logger.exception("Erro ao calcular pizza mes=%s uid=%s", mes_str, usuario_id)
        raise HTTPException(status_code=500, detail="Erro ao calcular distribuição de horas")

    # Base = capacidade disponível nos dias úteis.
    # Prioridade: (1) capacidade cadastrada, (2) total lançado, (3) dias úteis × 480 min.
    # O fallback garante que meses sem lançamento apareçam como 100% não alocado
    # em vez de mostrar "sem capacidade cadastrada".
    if total_capacidade > 0:
        base = total_capacidade
    elif total_lancado > 0:
        base = total_lancado
    else:
        base = _dias_uteis_do_mes(mes_inicio) * 480  # 8 h por dia útil
    nao_alocado = max(0, base - total_lancado)

    fatias = [
        PizzaFatia(
            nome=f["nome"],
            cor=f["cor"],
            minutos=f["minutos"],
            percentual=round(f["minutos"] / base * 100, 1) if base > 0 else 0.0,
        )
        for f in fatias_raw
    ]

    return PizzaDistribuicaoResponse(
        mes=mes_inicio.strftime("%Y-%m"),
        total_capacidade_min=base,
        nao_alocado_min=nao_alocado,
        fatias=fatias,
    )


# ---------------------------------------------------------------------------
# Rota /kpi/minha-distribuicao — operador
# ---------------------------------------------------------------------------


@router.get(
    "/minha-distribuicao",
    summary="Distribuição de lançamentos do usuário em um mês",
)
def minha_distribuicao(
    usuario: UsuarioLogado,
    request: Request,
    mes: str = Query(default="", description="Mês no formato YYYY-MM (default: mês atual)"),
) -> PizzaDistribuicaoResponse:
    """Retorna a distribuição de lançamentos do usuário autenticado em um determinado mês.

    Cada fatia representa um tipo de atividade com sua cor e percentual.
    A fatia 'Não alocado' representa a capacidade não utilizada.
    """
    engine_cp = request.app.state.engine_cp
    mes_inicio = _parse_mes(mes)
    return _pizza_query(engine_cp, mes_inicio, usuario.usuario_id)


# ---------------------------------------------------------------------------
# Rota /kpi/distribuicao-mensal — admin
# ---------------------------------------------------------------------------


@router.get(
    "/distribuicao-mensal",
    summary="Distribuição mensal de lançamentos (admin)",
)
def distribuicao_mensal(
    _: SomenteAdmin,
    request: Request,
    mes: str = Query(default="", description="Mês no formato YYYY-MM (default: mês atual)"),
    usuario_id: int = Query(default=0, description="ID do usuário (0 = todos os operadores)"),
) -> PizzaDistribuicaoResponse:
    """Retorna a distribuição de lançamentos de todos os operadores (ou de um específico) em um mês."""
    engine_cp = request.app.state.engine_cp
    mes_inicio = _parse_mes(mes)
    uid = usuario_id if usuario_id > 0 else None
    return _pizza_query(engine_cp, mes_inicio, uid)
