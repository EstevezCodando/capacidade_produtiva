"""Testes de integração para vw_ut_subfase_conclusao.

Valida a regra de negócio central:
  Uma (ut, subfase) está concluída somente quando TODAS as suas atividades
  têm tipo_situacao_id IN (4, 5).
  Qualquer atividade em 1=Não iniciada, 2=Em execução ou 3=Pausada bloqueia.

Cenários cobertos:
  1. Campos obrigatórios presentes na view (incluindo etapas_situacao)
  2. (ut, subfase) com atividades mistas → concluida = FALSE
  3. (ut, subfase) com todas finalizadas/não-finalizadas → concluida = TRUE
  4. total_pendentes == 0 implica concluida == TRUE (e vice-versa)
  5. situacoes_pendentes usa formato "TipoEtapa: Situação" e lista apenas bloqueantes
  6. etapas_situacao inclui TODAS as etapas no formato "TipoEtapa: Situação"
  7. Cenário de injeção manual — atividade Em execução bloqueia par já concluído
  8. Idempotência após múltiplos syncs
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.infrastructure.sap_sync.sync import sincronizar_sap_para_snapshot

_VIEW = "sap_analytics.vw_ut_subfase_conclusao"
_SEPARADOR = ": "
_SITUACOES_BLOQUEANTES_NOMES = {"Não iniciada", "Em execução", "Pausada"}
_TODAS_SITUACOES_NOMES = {"Não iniciada", "Em execução", "Pausada", "Finalizada", "Não finalizada"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _buscar(engine: Engine, sql: str, params: dict | None = None) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).fetchall()
    return [dict(r._mapping) for r in rows]


def _scalar(engine: Engine, sql: str, params: dict | None = None) -> object:
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar_one()


# ---------------------------------------------------------------------------
# 1. Estrutura da view
# ---------------------------------------------------------------------------

_CAMPOS_ESPERADOS = {
    "ut_id",
    "ut_nome",
    "subfase_id",
    "subfase_nome",
    "lote_id",
    "lote_nome",
    "bloco_id",
    "bloco_nome",
    "fase_id",
    "fase_nome",
    "projeto_id",
    "projeto_nome",
    "total_atividades",
    "total_concluidas",
    "total_pendentes",
    "etapas_situacao",
    "situacoes_pendentes",
    "concluida",
}


def test_vw_ut_subfase_conclusao_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    sql = text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'sap_analytics' AND table_name = 'vw_ut_subfase_conclusao'")
    with engine_cp.connect() as conn:
        colunas = {r[0] for r in conn.execute(sql).fetchall()}

    ausentes = _CAMPOS_ESPERADOS - colunas
    assert not ausentes, f"Campos ausentes em vw_ut_subfase_conclusao: {ausentes}"


# ---------------------------------------------------------------------------
# 2 & 3. Lógica de conclusão com dados do seed
# ---------------------------------------------------------------------------


def test_concluida_false_quando_ha_atividade_pendente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    pendentes = _buscar(engine_cp, f"SELECT * FROM {_VIEW} WHERE total_pendentes > 0")
    assert pendentes, "Seed deve conter pares (ut, subfase) com atividades pendentes"

    for row in pendentes:
        assert row["concluida"] is False, (
            f"ut_id={row['ut_id']} subfase_id={row['subfase_id']} tem total_pendentes={row['total_pendentes']} mas concluida=TRUE"
        )


def test_concluida_true_somente_quando_zero_pendentes(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    violacoes_true = _scalar(
        engine_cp,
        f"SELECT COUNT(*) FROM {_VIEW} WHERE concluida = TRUE AND total_pendentes > 0",
    )
    assert violacoes_true == 0, f"{violacoes_true} pares marcados concluida=TRUE com atividades pendentes"

    violacoes_false = _scalar(
        engine_cp,
        f"SELECT COUNT(*) FROM {_VIEW} WHERE concluida = FALSE AND total_pendentes = 0",
    )
    assert violacoes_false == 0, f"{violacoes_false} pares marcados concluida=FALSE sem nenhuma pendência"


def test_total_atividades_igual_concluidas_mais_pendentes(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    violacoes = _scalar(
        engine_cp,
        f"SELECT COUNT(*) FROM {_VIEW} WHERE total_atividades <> total_concluidas + total_pendentes",
    )
    assert violacoes == 0, f"{violacoes} pares com total_atividades != total_concluidas + total_pendentes"


# ---------------------------------------------------------------------------
# 4 & 5. Formato de situacoes_pendentes: "TipoEtapa: Situação"
# ---------------------------------------------------------------------------


def test_situacoes_pendentes_formato_etapa_situacao(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Cada entrada de situacoes_pendentes deve ter formato 'TipoEtapa: Situação'."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    rows = _buscar(
        engine_cp,
        f"SELECT situacoes_pendentes FROM {_VIEW} WHERE array_length(situacoes_pendentes, 1) > 0",
    )
    assert rows, "Seed deve conter pares com situacoes_pendentes preenchidas"

    for row in rows:
        for entrada in row["situacoes_pendentes"]:
            assert _SEPARADOR in entrada, f"Entrada '{entrada}' não segue o formato 'TipoEtapa: Situação'"
            _, situacao = entrada.split(_SEPARADOR, 1)
            assert situacao in _SITUACOES_BLOQUEANTES_NOMES, f"situacoes_pendentes contém situação não-bloqueante: '{situacao}'"


def test_situacoes_pendentes_vazio_quando_concluida(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    violacoes = _scalar(
        engine_cp,
        f"SELECT COUNT(*) FROM {_VIEW} WHERE concluida = TRUE AND array_length(situacoes_pendentes, 1) > 0",
    )
    assert violacoes == 0, f"{violacoes} pares concluídos ainda têm situacoes_pendentes preenchidas"


# ---------------------------------------------------------------------------
# 6. etapas_situacao: todas as etapas no formato "TipoEtapa: Situação"
# ---------------------------------------------------------------------------


def test_etapas_situacao_formato_etapa_situacao(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Cada entrada de etapas_situacao deve ter formato 'TipoEtapa: Situação'."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    rows = _buscar(
        engine_cp,
        f"SELECT etapas_situacao FROM {_VIEW} WHERE array_length(etapas_situacao, 1) > 0 LIMIT 20",
    )
    assert rows, "Seed deve produzir registros com etapas_situacao preenchido"

    for row in rows:
        for entrada in row["etapas_situacao"]:
            assert _SEPARADOR in entrada, f"Entrada '{entrada}' não segue o formato 'TipoEtapa: Situação'"
            _, situacao = entrada.split(_SEPARADOR, 1)
            assert situacao in _TODAS_SITUACOES_NOMES, f"etapas_situacao contém situação desconhecida: '{situacao}'"


def test_etapas_situacao_inclui_todas_as_situacoes(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """etapas_situacao deve ter pelo menos tantas entradas quanto total_atividades."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    violacoes = _scalar(
        engine_cp,
        f"SELECT COUNT(*) FROM {_VIEW} WHERE array_length(etapas_situacao, 1) < total_atividades",
    )
    assert violacoes == 0, f"{violacoes} pares com etapas_situacao menor que total_atividades"


def test_situacoes_pendentes_subconjunto_de_etapas_situacao(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Todo item de situacoes_pendentes deve aparecer em etapas_situacao."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    violacoes = _scalar(
        engine_cp,
        f"SELECT COUNT(*) FROM {_VIEW} WHERE NOT (situacoes_pendentes <@ etapas_situacao)",
    )
    assert violacoes == 0, f"{violacoes} pares onde situacoes_pendentes não é subconjunto de etapas_situacao"


# ---------------------------------------------------------------------------
# 7. Granularidade: cada linha é única por (ut_id, subfase_id)
# ---------------------------------------------------------------------------


def test_granularidade_ut_subfase_unica(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    duplicatas = _scalar(
        engine_cp,
        f"SELECT COUNT(*) FROM (  SELECT ut_id, subfase_id FROM {_VIEW}   GROUP BY ut_id, subfase_id HAVING COUNT(*) > 1) AS dup",
    )
    assert duplicatas == 0, f"{duplicatas} pares (ut_id, subfase_id) duplicados na view"


# ---------------------------------------------------------------------------
# 8. Injeção manual — atividade Em execução bloqueia par já concluído
# ---------------------------------------------------------------------------


def test_atividade_em_execucao_bloqueia_conclusao(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    concluidos = _buscar(
        engine_cp,
        f"SELECT ut_id, subfase_id FROM {_VIEW} WHERE concluida = TRUE LIMIT 1",
    )
    if not concluidos:
        pytest.skip("Seed não produziu nenhum par concluído para este cenário")

    ut_id = concluidos[0]["ut_id"]
    subfase_id = concluidos[0]["subfase_id"]

    etapa_rows = _buscar(
        engine_cp,
        "SELECT id FROM sap_snapshot.macrocontrole_etapa WHERE subfase_id = :sf LIMIT 1",
        {"sf": subfase_id},
    )
    assert etapa_rows, f"Nenhuma etapa encontrada para subfase_id={subfase_id}"
    etapa_id = etapa_rows[0]["id"]

    with engine_cp.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO sap_snapshot.macrocontrole_atividade "
                "(id, etapa_id, unidade_trabalho_id, usuario_id, tipo_situacao_id, "
                " data_inicio, data_fim, observacao) "
                "VALUES (99997, :etapa, :ut, NULL, 2, NULL, NULL, 'injecao_teste_bloqueio') "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"etapa": etapa_id, "ut": ut_id},
        )

    resultado = _buscar(
        engine_cp,
        f"SELECT concluida, total_pendentes, situacoes_pendentes, etapas_situacao FROM {_VIEW} WHERE ut_id = :ut AND subfase_id = :sf",
        {"ut": ut_id, "sf": subfase_id},
    )
    assert resultado, "Par (ut, subfase) sumiu da view após injeção"

    row = resultado[0]
    assert row["concluida"] is False
    assert row["total_pendentes"] >= 1

    pendentes_str = " | ".join(row["situacoes_pendentes"])
    assert "Em execução" in pendentes_str, f"'Em execução' não encontrada em situacoes_pendentes: {row['situacoes_pendentes']}"

    etapas_str = " | ".join(row["etapas_situacao"])
    assert "Em execução" in etapas_str, f"'Em execução' não encontrada em etapas_situacao: {row['etapas_situacao']}"

    with engine_cp.begin() as conn:
        conn.execute(text("DELETE FROM sap_snapshot.macrocontrole_atividade WHERE id = 99997"))


# ---------------------------------------------------------------------------
# 9. Idempotência após múltiplos syncs
# ---------------------------------------------------------------------------


def test_resultado_estavel_apos_multiplos_syncs(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    count_1 = _scalar(engine_cp, f"SELECT COUNT(*) FROM {_VIEW}")

    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    count_2 = _scalar(engine_cp, f"SELECT COUNT(*) FROM {_VIEW}")

    assert count_1 == count_2, f"Contagem instável entre syncs: {count_1} → {count_2}"
