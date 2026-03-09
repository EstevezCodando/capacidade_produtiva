"""Testes de integração para as views analíticas do schema sap_analytics.

Cobertura dos critérios de aceite da Sprint 1.3:
  1. vw_ut_enriquecida contém os campos obrigatórios
  2. vw_atividade_enriquecida contém os campos obrigatórios
  3. is_finalizada é True somente quando tipo_situacao_id = 4
  4. vw_ut_atividade contém o join completo
  5. As views são recriadas automaticamente após sincronização
  6. Idempotência: garantir_views pode ser chamado N vezes sem erro
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.infrastructure.sap_sync.analytics_manager import garantir_views_analytics
from cp.infrastructure.sap_sync.sync import sincronizar_sap_para_snapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCHEMA = "sap_analytics"


def _colunas_da_view(engine: Engine, view: str) -> set[str]:
    """Retorna o conjunto de nomes de colunas de uma view."""
    sql = text("SELECT column_name FROM information_schema.columns WHERE table_schema = :schema AND table_name = :view")
    with engine.connect() as conn:
        rows = conn.execute(sql, {"schema": _SCHEMA, "view": view}).fetchall()
    return {r[0] for r in rows}


def _contar_view(engine: Engine, view: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {_SCHEMA}.{view}")).scalar_one()


def _buscar_view(engine: Engine, view: str) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"SELECT * FROM {_SCHEMA}.{view}")).fetchall()
    return [dict(r._mapping) for r in rows]


# ---------------------------------------------------------------------------
# Critério 1 — vw_ut_enriquecida: campos obrigatórios
# ---------------------------------------------------------------------------

_CAMPOS_UT = {
    "projeto_id",
    "projeto_nome",
    "lote_id",
    "lote_nome",
    "bloco_id",
    "bloco_nome",
    "subfase_id",
    "subfase_nome",
    "fase_id",
    "fase_nome",
    "ut_id",
    "ut_nome",
    "dificuldade",
    "tempo_estimado_minutos",
}


def test_vw_ut_enriquecida_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    colunas = _colunas_da_view(engine_cp, "vw_ut_enriquecida")
    ausentes = _CAMPOS_UT - colunas
    assert not ausentes, f"Campos ausentes em vw_ut_enriquecida: {ausentes}"


# ---------------------------------------------------------------------------
# Critério 2 — vw_atividade_enriquecida: campos obrigatórios
# ---------------------------------------------------------------------------

_CAMPOS_ATIVIDADE = {
    "atividade_id",
    "unidade_trabalho_id",
    "etapa_id",
    "tipo_etapa_id",
    "tipo_etapa_nome",
    "tipo_situacao_id",
    "tipo_situacao_nome",
    "usuario_id",
    "usuario_nome",
    "data_inicio",
    "data_fim",
    "observacao",
    "is_finalizada",
}


def test_vw_atividade_enriquecida_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    colunas = _colunas_da_view(engine_cp, "vw_atividade_enriquecida")
    ausentes = _CAMPOS_ATIVIDADE - colunas
    assert not ausentes, f"Campos ausentes em vw_atividade_enriquecida: {ausentes}"


# ---------------------------------------------------------------------------
# Critério 3 — is_finalizada somente quando tipo_situacao_id = 4
# ---------------------------------------------------------------------------


def test_is_finalizada_verdadeiro_somente_para_tipo_situacao_4(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    sql = text(f"SELECT tipo_situacao_id, is_finalizada FROM {_SCHEMA}.vw_atividade_enriquecida")
    with engine_cp.connect() as conn:
        rows = conn.execute(sql).fetchall()

    assert rows, "View não retornou registros após sync"

    for row in rows:
        tipo_situacao_id = row[0]
        is_finalizada = row[1]
        if tipo_situacao_id == 4:
            assert is_finalizada is True, f"tipo_situacao_id=4 deveria ter is_finalizada=True, mas foi {is_finalizada}"
        else:
            assert is_finalizada is False, f"tipo_situacao_id={tipo_situacao_id} deveria ter is_finalizada=False, mas foi {is_finalizada}"


def test_is_finalizada_false_para_situacoes_nao_4(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Verifica que situações 1, 2, 3, 5 nunca geram is_finalizada=True."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    sql = text(f"SELECT COUNT(*) FROM {_SCHEMA}.vw_atividade_enriquecida WHERE tipo_situacao_id <> 4 AND is_finalizada = TRUE")
    with engine_cp.connect() as conn:
        count = conn.execute(sql).scalar_one()

    assert count == 0, f"{count} registros com tipo_situacao_id<>4 marcados como is_finalizada"


# ---------------------------------------------------------------------------
# Critério 4 — vw_ut_atividade: join completo
# ---------------------------------------------------------------------------

_CAMPOS_UT_ATIVIDADE = {
    "lote_id",
    "lote_nome",
    "bloco_id",
    "bloco_nome",
    "subfase_id",
    "subfase_nome",
    "ut_id",
    "ut_nome",
    "dificuldade",
    "atividade_id",
    "tipo_etapa_id",
    "tipo_etapa_nome",
    "tipo_situacao_id",
    "tipo_situacao_nome",
    "usuario_id",
    "usuario_nome",
    "observacao",
    "is_finalizada",
    "data_inicio",
    "data_fim",
}


def test_vw_ut_atividade_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    colunas = _colunas_da_view(engine_cp, "vw_ut_atividade")
    ausentes = _CAMPOS_UT_ATIVIDADE - colunas
    assert not ausentes, f"Campos ausentes em vw_ut_atividade: {ausentes}"


def test_vw_ut_atividade_retorna_dados_apos_sync(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    count = _contar_view(engine_cp, "vw_ut_atividade")
    assert count > 0, "vw_ut_atividade não retornou registros após sync"


def test_vw_ut_atividade_join_correto(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Verifica que lote/bloco/subfase dos registros são consistentes com a UT."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    sql = text(f"SELECT COUNT(*) FROM {_SCHEMA}.vw_ut_atividade WHERE lote_id IS NULL OR bloco_id IS NULL OR subfase_id IS NULL")
    with engine_cp.connect() as conn:
        nulls = conn.execute(sql).scalar_one()

    assert nulls == 0, f"{nulls} registros com lote/bloco/subfase nulos em vw_ut_atividade"


# ---------------------------------------------------------------------------
# Critério 5 — Views existem e são consultáveis após sync (integração)
# ---------------------------------------------------------------------------


def test_todas_as_views_existem_apos_sync(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Garante que o pipeline de sync cria/mantém as três views."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    views = ["vw_ut_enriquecida", "vw_atividade_enriquecida", "vw_ut_atividade"]
    for view in views:
        sql = text("SELECT 1 FROM information_schema.views WHERE table_schema = 'sap_analytics' AND table_name = :view")
        with engine_cp.connect() as conn:
            exists = conn.execute(sql, {"view": view}).scalar()
        assert exists == 1, f"View {view} não encontrada após sync"


def test_vw_ut_enriquecida_retorna_dados_apos_sync(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    count = _contar_view(engine_cp, "vw_ut_enriquecida")
    assert count > 0, "vw_ut_enriquecida não retornou registros após sync"


def test_vw_atividade_enriquecida_retorna_dados_apos_sync(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    count = _contar_view(engine_cp, "vw_atividade_enriquecida")
    assert count > 0, "vw_atividade_enriquecida não retornou registros após sync"


# ---------------------------------------------------------------------------
# Critério 6 — Idempotência de garantir_views_analytics
# ---------------------------------------------------------------------------


def test_garantir_views_idempotente(engine_cp: Engine) -> None:
    """garantir_views pode ser chamado múltiplas vezes sem erro nem duplicação."""
    for _ in range(3):
        garantir_views_analytics(engine_cp)

    views = ["vw_ut_enriquecida", "vw_atividade_enriquecida", "vw_ut_atividade"]
    for view in views:
        sql = text("SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'sap_analytics' AND table_name = :view")
        with engine_cp.connect() as conn:
            count = conn.execute(sql, {"view": view}).scalar_one()
        assert count == 1, f"View {view} deveria existir exatamente 1 vez, encontrou {count}"


# ---------------------------------------------------------------------------
# Integridade dos dados — sanidade cruzada
# ---------------------------------------------------------------------------


def test_usuario_nulo_permitido_em_atividade_enriquecida(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Atividades sem usuário (tipo_situacao_id=1, não iniciada) não devem ser excluídas."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    sql = text(f"SELECT COUNT(*) FROM {_SCHEMA}.vw_atividade_enriquecida WHERE usuario_id IS NULL")
    with engine_cp.connect() as conn:
        sem_usuario = conn.execute(sql).scalar_one()

    assert sem_usuario > 0, "Esperavam-se atividades sem usuário (não iniciadas) — seed contém registros assim"


def test_tipo_situacao_nome_preenchido(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """tipo_situacao_nome nunca deve ser nulo nas atividades enriquecidas."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    sql = text(f"SELECT COUNT(*) FROM {_SCHEMA}.vw_atividade_enriquecida WHERE tipo_situacao_nome IS NULL")
    with engine_cp.connect() as conn:
        nulos = conn.execute(sql).scalar_one()

    assert nulos == 0, f"{nulos} registros com tipo_situacao_nome nulo"
