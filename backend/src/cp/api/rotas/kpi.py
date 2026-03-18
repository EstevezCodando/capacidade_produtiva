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

import logging
from typing import Any

from fastapi import APIRouter, Request
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
        pass

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


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------


@router.get("/projetos", summary="KPI agregado por projeto")
def kpi_projetos(_: UsuarioLogado, request: Request) -> KpiProjetosResponse:
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
        pass

    return KpiProjetosResponse(
        sap_snapshot_atualizado_em=snapshot_ts,
        kpi_calculado_em=kpi_ts,
        projetos=projetos,
    )


@router.get("/projetos/{projeto_id}", summary="KPI do projeto por bloco e subfase")
def kpi_projeto_detalhe(projeto_id: int, _: UsuarioLogado, request: Request) -> KpiProjetoDetalhe:
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
        pass

    return KpiProjetoDetalhe(
        projeto_id=projeto_id,
        projeto_nome=projeto_nome,
        sap_snapshot_atualizado_em=snapshot_ts,
        kpi_calculado_em=kpi_ts,
        lotes=lotes if "lotes" in dir() else [],
        blocos=blocos_list,
    )


@router.get("/subfase/{subfase_id}", summary="UTs de uma subfase")
def kpi_subfase(subfase_id: int, _: UsuarioLogado, request: Request) -> KpiSubfaseDetalhe:
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
        pass

    return KpiSubfaseDetalhe(
        subfase_id=subfase_id,
        subfase_nome=subfase_nome,
        sap_snapshot_atualizado_em=snapshot_ts,
        kpi_calculado_em=kpi_ts,
        uts=uts,
    )


@router.get("/uts/{ut_id}", summary="Detalhe completo de uma UT")
def kpi_ut(ut_id: int, _: UsuarioLogado, request: Request) -> KpiUtDetalhe:
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
        pass

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
def kpi_inconsistencias(_: SomenteAdmin, request: Request) -> InconsistenciasResponse:
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
        pass

    return InconsistenciasResponse(
        total=len(itens),
        sap_snapshot_atualizado_em=snapshot_ts,
        itens=itens,
    )


@router.get("/dashboard", summary="Dashboard completo com hierarquia e destaques")
def kpi_dashboard(_: UsuarioLogado, request: Request) -> DashboardResponse:
    """Dashboard consolidado com progresso geral, hierarquia de projetos e top performers."""
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

    try:
        with engine_cp.connect() as conn:
            # 1. Contagem de projetos ativos
            result = conn.execute(text("SELECT COUNT(*) FROM sap_snapshot.macrocontrole_projeto WHERE status_id = 1"))
            row = result.fetchone()
            projetos_ativos = row[0] if row else 0

            # 1.1. Contagem de blocos cadastrados no snapshot SAP
            result = conn.execute(text("SELECT COUNT(*) FROM sap_snapshot.macrocontrole_bloco"))
            row = result.fetchone()
            blocos_sap_cadastrados = int(row[0]) if row else 0

            # 1.2. Horas previstas e horas lançadas em produção (bloco)
            result = conn.execute(
                text("""
                SELECT
                    COALESCE(SUM(ap.minutos_planejados_normais + ap.minutos_planejados_extras), 0) AS horas_previstas_producao_min,
                    COALESCE((
                        SELECT SUM(al.minutos)
                        FROM capacidade.agenda_lancamento al
                        JOIN capacidade.tipo_atividade ta ON ta.id = al.tipo_atividade_id
                        WHERE al.em_uso = TRUE
                          AND ta.codigo = 'BLOCO'
                    ), 0) AS horas_lancadas_producao_min
                FROM capacidade.agenda_prevista_admin ap
                WHERE ap.em_uso = TRUE
                  AND ap.bloco_id IS NOT NULL
                """)
            )
            row = result.fetchone()
            if row:
                horas_previstas_producao_min = int(row.horas_previstas_producao_min or 0)
                horas_lancadas_producao_min = int(row.horas_lancadas_producao_min or 0)

            # 2. Pontos totais e realizados
            result = conn.execute(
                text("""
                SELECT 
                    COALESCE(SUM(e.ut_dificuldade), 0) as pontos_totais,
                    COALESCE(SUM(
                        COALESCE(d.pontos_executor, 0) + 
                        COALESCE(d.pontos_revisor, 0) + 
                        COALESCE(d.pontos_corretor, 0)
                    ), 0) as pontos_realizados
                FROM kpi.estado_ut e
                LEFT JOIN kpi.distribuicao_pontos d ON d.ut_id = e.ut_id
            """)
            )
            row = result.fetchone()
            if row:
                pontos_totais = float(row.pontos_totais or 0)
                pontos_realizados = float(row.pontos_realizados or 0)

            # 3. Hierarquia: Projeto -> Lote -> Bloco -> Subfase
            sql = text("""
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
                WHERE p.status_id = 1
                GROUP BY p.id, p.nome, l.id, l.nome, b.id, b.nome, sf.id, sf.nome, tf.nome, tf.cor
                ORDER BY p.nome, l.nome, b.nome, sf.nome
            """)
            result = conn.execute(sql)

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
            sql = text("""
                SELECT 
                    u.id as usuario_id,
                    u.nome,
                    u.nome_guerra,
                    SUM(d.pontos_executor) as pontos
                FROM kpi.distribuicao_pontos d
                JOIN sap_snapshot.dgeo_usuario u ON u.id = d.executor_id
                WHERE d.pontos_executor > 0
                GROUP BY u.id, u.nome, u.nome_guerra
                ORDER BY pontos DESC
                LIMIT 1
            """)
            result = conn.execute(sql)
            row = result.fetchone()
            if row:
                top_executor = TopUsuario(
                    usuario_id=row.usuario_id,
                    nome=row.nome,
                    nome_guerra=row.nome_guerra,
                    pontos=float(row.pontos),
                )

            # 5. Top revisor
            sql = text("""
                SELECT 
                    u.id as usuario_id,
                    u.nome,
                    u.nome_guerra,
                    SUM(d.pontos_revisor) as pontos
                FROM kpi.distribuicao_pontos d
                JOIN sap_snapshot.dgeo_usuario u ON u.id = d.revisor_id
                WHERE d.pontos_revisor > 0
                GROUP BY u.id, u.nome, u.nome_guerra
                ORDER BY pontos DESC
                LIMIT 1
            """)
            result = conn.execute(sql)
            row = result.fetchone()
            if row:
                top_revisor = TopUsuario(
                    usuario_id=row.usuario_id,
                    nome=row.nome,
                    nome_guerra=row.nome_guerra,
                    pontos=float(row.pontos),
                )

            # 6. Busca os Top Executores por Subfase
            sql_exec = text("""
                WITH ranking AS (
                    SELECT 
                        e.subfase_id, e.subfase_nome, d.executor_id as usr_id, u.nome, u.nome_guerra,
                        SUM(d.pontos_executor) as pontos,
                        ROW_NUMBER() OVER(PARTITION BY e.subfase_id ORDER BY SUM(d.pontos_executor) DESC) as rn
                    FROM kpi.estado_ut e
                    JOIN kpi.distribuicao_pontos d ON e.ut_id = d.ut_id
                    JOIN sap_snapshot.dgeo_usuario u ON u.id = d.executor_id
                    WHERE d.pontos_executor > 0
                    GROUP BY e.subfase_id, e.subfase_nome, d.executor_id, u.nome, u.nome_guerra
                )
                SELECT subfase_id, subfase_nome, usr_id, nome, nome_guerra, pontos
                FROM ranking WHERE rn = 1
            """)
            for row in conn.execute(sql_exec):
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
            sql_rev = text("""
                WITH ranking AS (
                    SELECT 
                        e.subfase_id, e.subfase_nome, d.revisor_id as usr_id, u.nome, u.nome_guerra,
                        SUM(d.pontos_revisor) as pontos,
                        ROW_NUMBER() OVER(PARTITION BY e.subfase_id ORDER BY SUM(d.pontos_revisor) DESC) as rn
                    FROM kpi.estado_ut e
                    JOIN kpi.distribuicao_pontos d ON e.ut_id = d.ut_id
                    JOIN sap_snapshot.dgeo_usuario u ON u.id = d.revisor_id
                    WHERE d.pontos_revisor > 0
                    GROUP BY e.subfase_id, e.subfase_nome, d.revisor_id, u.nome, u.nome_guerra
                )
                SELECT subfase_id, subfase_nome, usr_id, nome, nome_guerra, pontos
                FROM ranking WHERE rn = 1
            """)
            for row in conn.execute(sql_rev):
                top_revisores_subfase.append(
                    {
                        "subfase_id": row.subfase_id,
                        "usuario_id": row.usr_id,
                        "nome": row.nome,
                        "nome_guerra": row.nome_guerra,
                        "pontos": float(row.pontos),
                    }
                )
    except Exception:
        pass

    progresso_geral = (pontos_realizados / pontos_totais * 100) if pontos_totais > 0 else None

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
    )


# ---------------------------------------------------------------------------
# Modelos — Dashboard do usuário (operador)
# ---------------------------------------------------------------------------

class PontosSubfaseResposta(BaseModel):
    subfase_id: int
    subfase_nome: str
    pontos: float


class BlocoDetalheUsuario(BaseModel):
    bloco_id: int
    bloco_nome: str
    projeto_nome: str
    pontos_total_bloco: float
    pontos_usuario_bloco: float
    como_executor: list[PontosSubfaseResposta]
    como_revisor: list[PontosSubfaseResposta]
    como_corretor: list[PontosSubfaseResposta]


class DiaHorasResposta(BaseModel):
    data: str
    minutos_previstos: int
    minutos_lancados: int


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


# ---------------------------------------------------------------------------
# Rota /kpi/meu-dashboard
# ---------------------------------------------------------------------------


@router.get("/meu-dashboard", summary="Dashboard do usuário autenticado")
def meu_dashboard(usuario: UsuarioLogado, request: Request) -> MeuDashboardResposta:
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
                           SUM(al.minutos) AS minutos
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
                    COALESCE(l.minutos, 0) AS minutos_lancados
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
                ))
    except Exception:
        _logger.exception("Erro ao calcular meu-dashboard para usuario_id=%s", uid)

    blocos_list = sorted(blocos_map.values(), key=lambda b: b.bloco_nome)
    pontos_total_geral   = sum(b.pontos_total_bloco   for b in blocos_list)
    pontos_usuario_geral = sum(b.pontos_usuario_bloco for b in blocos_list)

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
    )
