"""Testes de integração para as 6 tabelas normalizadas do pipeline KPI.

Cada tabela tem sua própria seção de testes, cobrindo:
  - Estrutura (colunas obrigatórias presentes)
  - Invariantes de dados (constraints lógicas que sempre devem ser verdade)
  - Regras de negócio específicas da tabela
  - Rastreabilidade (decisões auditáveis independentemente)

Tabelas testadas:
  kpi.fluxo_ut          — ciclo detectado + atividades vigentes
  kpi.participantes_ut  — participantes normalizados por papel
  kpi.validacao_fluxo   — fluxo fechado / etapa bloqueante
  kpi.validacao_nota    — nota extraída e validada
  kpi.pontos_usuario    — pontos calculados por (ut, papel)
  kpi.estado_ut         — estado consolidado da UT
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.infrastructure.sap_sync.sync import sincronizar_sap_para_snapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CICLOS_VALIDOS = {
    "CICLO_1_PADRAO",
    "CICLO_2_REVISAO_CORRECAO",
    "CICLO_3_SEM_CORRECAO",
    "CICLO_4_REVISAO_FINAL",
    "INCONSISTENTE_CICLO",
}

_PAPEIS_VALIDOS = {
    "EXECUTOR",
    "REVISOR",
    "CORRETOR",
    "REVISOR_CORRECAO",
    "REVISOR_FINAL",
}

_ESTADOS_VALIDOS = {
    "UT BLOQUEADA",
    "INCONSISTENTE_DIFICULDADE",
    "INCONSISTENTE_CICLO",
    "PENDENTE_EXECUCAO",
    "PENDENTE_REVISAO",
    "PENDENTE_CORRECAO",
    "INCONSISTENTE_NOTA",
    "CONCLUIDA_COM_N_Finalizada",
    "CONCLUIDA_SEM_CORRECAO",
    "CONCLUIDA_COM_CORRECAO",
}


def _buscar(engine: Engine, sql: str, params: dict | None = None) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).fetchall()
    return [dict(r._mapping) for r in rows]


def _scalar(engine: Engine, sql: str, params: dict | None = None) -> object:
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar_one()


def _colunas(engine: Engine, schema: str, tabela: str) -> set[str]:
    sql = text("SELECT column_name FROM information_schema.columns WHERE table_schema = :s AND table_name = :t")
    with engine.connect() as conn:
        return {r[0] for r in conn.execute(sql, {"s": schema, "t": tabela}).fetchall()}


# ===========================================================================
# 1. kpi.fluxo_ut
# ===========================================================================

_CAMPOS_FLUXO_UT = {
    "ut_id",
    "projeto_nome",
    "lote_nome",
    "bloco_nome",
    "fase_nome",
    "subfase_nome",
    "ut_disponivel",
    "ut_dificuldade",
    "ciclo_modelo",
    "exec_atividade_id",
    "exec_usuario_id",
    "exec_tipo_situacao_id",
    "exec_tipo_situacao_nome",
    "rev_atividade_id",
    "rev_usuario_id",
    "rev_tipo_situacao_id",
    "rev_tipo_situacao_nome",
    "cor_atividade_id",
    "cor_usuario_id",
    "cor_tipo_situacao_id",
    "cor_tipo_situacao_nome",
    "cor_observacao",
    "revcor_atividade_id",
    "revcor_usuario_id",
    "revcor_tipo_situacao_id",
    "revcor_tipo_situacao_nome",
    "revfinal_atividade_id",
    "revfinal_usuario_id",
    "revfinal_tipo_situacao_id",
    "exec_ambigua",
    "rev_ambigua",
    "cor_ambigua",
    "revcor_ambigua",
    "revfinal_ambigua",
    "total_atividades",
    "total_finalizadas",
    "total_nao_finalizadas",
    "total_pendentes",
    "possui_nao_finalizada_no_historico",
    "somente_finalizada_ou_nao_finalizada",
    "observacoes_concatenadas",
    "data_inicio_fluxo",
    "data_fim_fluxo",
}


def test_fluxo_ut_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    ausentes = _CAMPOS_FLUXO_UT - _colunas(engine_cp, "kpi", "fluxo_ut")
    assert not ausentes, f"Campos ausentes em kpi.fluxo_ut: {ausentes}"


def test_fluxo_ut_chave_primaria_unica(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    dups = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM (SELECT ut_id FROM kpi.fluxo_ut GROUP BY ut_id HAVING COUNT(*) > 1) x",
    )
    assert dups == 0, f"{dups} ut_id duplicados em kpi.fluxo_ut"


def test_fluxo_ut_ciclo_modelo_sempre_valido(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    ciclos = {r["ciclo_modelo"] for r in _buscar(engine_cp, "SELECT DISTINCT ciclo_modelo FROM kpi.fluxo_ut")}
    invalidos = ciclos - _CICLOS_VALIDOS
    assert not invalidos, f"ciclo_modelo inválido em kpi.fluxo_ut: {invalidos}"


def test_fluxo_ut_exec_presente_em_todos_ciclos_validos(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Todo ciclo válido (não INCONSISTENTE) tem exec_atividade_id preenchido."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut WHERE ciclo_modelo <> 'INCONSISTENTE_CICLO' AND exec_atividade_id IS NULL",
    )
    assert violacoes == 0, f"{violacoes} UTs com ciclo válido mas sem exec_atividade_id"


def test_fluxo_ut_total_atividades_consistente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """total_finalizadas + total_nao_finalizadas + total_pendentes = total_atividades."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut WHERE total_finalizadas + total_nao_finalizadas + total_pendentes <> total_atividades",
    )
    assert violacoes == 0, f"{violacoes} UTs com contagem inconsistente em kpi.fluxo_ut"


def test_fluxo_ut_idempotente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    c1 = _scalar(engine_cp, "SELECT COUNT(*) FROM kpi.fluxo_ut")
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    c2 = _scalar(engine_cp, "SELECT COUNT(*) FROM kpi.fluxo_ut")
    assert c1 == c2, f"kpi.fluxo_ut instável entre syncs: {c1} → {c2}"


def test_fluxo_ut_data_inicio_anterior_ou_igual_fim(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """data_inicio_fluxo <= data_fim_fluxo quando ambas estão preenchidas."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut WHERE data_inicio_fluxo IS NOT NULL AND data_fim_fluxo IS NOT NULL AND data_inicio_fluxo > data_fim_fluxo",
    )
    assert violacoes == 0, f"{violacoes} UTs com data_inicio_fluxo > data_fim_fluxo"


def test_fluxo_ut_concluidas_tem_ambas_datas(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """UTs com fluxo fechado devem ter data_inicio e data_fim preenchidas."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut f "
        "JOIN kpi.validacao_fluxo vf ON vf.ut_id = f.ut_id "
        "WHERE vf.fluxo_fechado = TRUE "
        "AND (f.data_inicio_fluxo IS NULL OR f.data_fim_fluxo IS NULL)",
    )
    assert violacoes == 0, f"{violacoes} UTs com fluxo fechado sem datas de início/fim"


# ===========================================================================
# 2. kpi.participantes_ut
# ===========================================================================

_CAMPOS_PARTICIPANTES = {
    "ut_id",
    "papel",
    "atividade_id",
    "usuario_id",
    "usuario_nome",
    "tipo_situacao_id",
    "tipo_situacao_nome",
    "eh_revisao_vigente",
}


def test_participantes_ut_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    ausentes = _CAMPOS_PARTICIPANTES - _colunas(engine_cp, "kpi", "participantes_ut")
    assert not ausentes, f"Campos ausentes em kpi.participantes_ut: {ausentes}"


def test_participantes_ut_papeis_validos(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    papeis = {r["papel"] for r in _buscar(engine_cp, "SELECT DISTINCT papel FROM kpi.participantes_ut")}
    invalidos = papeis - _PAPEIS_VALIDOS
    assert not invalidos, f"Papéis inválidos em kpi.participantes_ut: {invalidos}"


def test_participantes_ut_toda_ut_tem_executor(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Toda UT com ciclo válido deve ter ao menos um participante EXECUTOR."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut f "
        "WHERE f.ciclo_modelo <> 'INCONSISTENTE_CICLO' "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM kpi.participantes_ut p "
        "  WHERE p.ut_id = f.ut_id AND p.papel = 'EXECUTOR'"
        ")",
    )
    assert violacoes == 0, f"{violacoes} UTs com ciclo válido sem EXECUTOR em participantes_ut"


def test_participantes_ut_exatamente_um_revisor_vigente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Cada UT com ciclo válido e etapa de revisão tem exatamente 1 eh_revisao_vigente=TRUE."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM ("
        "  SELECT ut_id, COUNT(*) AS qtd "
        "  FROM kpi.participantes_ut "
        "  WHERE eh_revisao_vigente = TRUE "
        "  GROUP BY ut_id HAVING COUNT(*) > 1"
        ") x",
    )
    assert violacoes == 0, f"{violacoes} UTs com mais de 1 eh_revisao_vigente em participantes_ut"


def test_participantes_ut_ut_ids_subset_de_fluxo_ut(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Todos os ut_id em participantes_ut devem existir em fluxo_ut."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    orphans = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.participantes_ut p WHERE NOT EXISTS (SELECT 1 FROM kpi.fluxo_ut f WHERE f.ut_id = p.ut_id)",
    )
    assert orphans == 0, f"{orphans} participantes sem UT em kpi.fluxo_ut"


# ===========================================================================
# 3. kpi.validacao_fluxo
# ===========================================================================

_CAMPOS_VALIDACAO_FLUXO = {
    "ut_id",
    "ciclo_modelo",
    "exec_finalizada",
    "revisao_vigente_finalizada",
    "cor_finalizada",
    "fluxo_fechado",
    "etapa_bloqueante",
}


def test_validacao_fluxo_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    ausentes = _CAMPOS_VALIDACAO_FLUXO - _colunas(engine_cp, "kpi", "validacao_fluxo")
    assert not ausentes, f"Campos ausentes em kpi.validacao_fluxo: {ausentes}"


def test_validacao_fluxo_fluxo_fechado_implica_sem_bloqueante(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Quando fluxo_fechado=TRUE, etapa_bloqueante deve ser NULL."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_fluxo WHERE fluxo_fechado = TRUE AND etapa_bloqueante IS NOT NULL",
    )
    assert violacoes == 0, f"{violacoes} UTs com fluxo_fechado=TRUE mas etapa_bloqueante preenchida"


def test_validacao_fluxo_aberto_implica_bloqueante(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Quando fluxo_fechado=FALSE e ciclo válido, etapa_bloqueante deve ser preenchida."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_fluxo WHERE fluxo_fechado = FALSE AND ciclo_modelo <> 'INCONSISTENTE_CICLO' AND etapa_bloqueante IS NULL",
    )
    assert violacoes == 0, f"{violacoes} UTs com fluxo aberto e ciclo válido sem etapa_bloqueante"


def test_validacao_fluxo_cobertura_total(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """kpi.validacao_fluxo deve ter exatamente as mesmas UTs que kpi.fluxo_ut."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    diff = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut f WHERE NOT EXISTS (SELECT 1 FROM kpi.validacao_fluxo v WHERE v.ut_id = f.ut_id)",
    )
    assert diff == 0, f"{diff} UTs em fluxo_ut sem linha em validacao_fluxo"


def test_validacao_fluxo_ciclo_1_cor_finalizada_presente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """CICLO_1_PADRAO sempre tem cor_finalizada preenchida (não NULL)."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_fluxo WHERE ciclo_modelo = 'CICLO_1_PADRAO' AND cor_finalizada IS NULL",
    )
    assert violacoes == 0, f"{violacoes} UTs CICLO_1 com cor_finalizada NULL"


def test_validacao_fluxo_ciclos_sem_correcao_cor_null(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Ciclos 2, 3 e 4 não têm correção — cor_finalizada deve ser NULL."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_fluxo "
        "WHERE ciclo_modelo IN ('CICLO_2_REVISAO_CORRECAO', 'CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL') "
        "AND cor_finalizada IS NOT NULL",
    )
    assert violacoes == 0, f"{violacoes} UTs sem correção com cor_finalizada preenchida"


# ===========================================================================
# 4. kpi.validacao_nota
# ===========================================================================

_CAMPOS_VALIDACAO_NOTA = {
    "ut_id",
    "ciclo_modelo",
    "nota_qualidade",
    "texto_qualidade",
    "nota_valida",
    "ocorrencia",
}


def test_validacao_nota_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    ausentes = _CAMPOS_VALIDACAO_NOTA - _colunas(engine_cp, "kpi", "validacao_nota")
    assert not ausentes, f"Campos ausentes em kpi.validacao_nota: {ausentes}"


def test_validacao_nota_ciclos_sem_nota_sempre_validos(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Ciclos 3 e 4 não exigem nota — nota_valida sempre TRUE, nota_qualidade NULL."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    violacoes_validade = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_nota WHERE ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL') AND nota_valida = FALSE",
    )
    assert violacoes_validade == 0, f"{violacoes_validade} UTs sem nota marcadas nota_valida=FALSE"

    violacoes_nota = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_nota "
        "WHERE ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL') "
        "AND nota_qualidade IS NOT NULL",
    )
    assert violacoes_nota == 0, f"{violacoes_nota} UTs sem nota com nota_qualidade preenchida"


def test_validacao_nota_nota_valida_entre_1_e_9(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Quando nota_qualidade está preenchida, deve ser entre 1 e 9."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_nota WHERE nota_qualidade IS NOT NULL AND nota_qualidade NOT BETWEEN 1 AND 9",
    )
    assert violacoes == 0, f"{violacoes} UTs com nota_qualidade fora de 1–9"


def test_validacao_nota_ocorrencia_nunca_null(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """ocorrencia é NOT NULL para todas as UTs — classifica todos os ciclos."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_nota WHERE ocorrencia IS NULL",
    )
    assert violacoes == 0, f"{violacoes} UTs com ocorrencia NULL"


def test_validacao_nota_ocorrencia_valores_validos(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """ocorrencia deve ser um dos 5 valores definidos."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    invalidos = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_nota "
        "WHERE ocorrencia NOT IN ("
        "  'NOTA_VALIDA', 'NOTA_AUSENTE', 'NOTA_INVALIDA', "
        "  'DISTRIBUICAO_DEFAULT', 'CICLO_INVALIDO'"
        ")",
    )
    assert invalidos == 0, f"{invalidos} UTs com ocorrencia fora dos valores definidos"


def test_validacao_nota_invalida_ocorrencia_coerente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """nota_valida=FALSE implica ocorrencia IN ('NOTA_AUSENTE', 'NOTA_INVALIDA')."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_nota WHERE nota_valida = FALSE AND ocorrencia NOT IN ('NOTA_AUSENTE', 'NOTA_INVALIDA')",
    )
    assert violacoes == 0, f"{violacoes} UTs com nota_valida=FALSE mas ocorrencia inconsistente"


def test_validacao_nota_valida_ocorrencia_coerente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """nota_valida=TRUE implica ocorrencia IN ('NOTA_VALIDA', 'DISTRIBUICAO_DEFAULT', 'CICLO_INVALIDO')."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_nota "
        "WHERE nota_valida = TRUE "
        "AND ocorrencia NOT IN ('NOTA_VALIDA', 'DISTRIBUICAO_DEFAULT', 'CICLO_INVALIDO')",
    )
    assert violacoes == 0, f"{violacoes} UTs com nota_valida=TRUE mas ocorrencia inconsistente"


def test_validacao_nota_cobertura_total(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """kpi.validacao_nota deve cobrir todas as UTs de kpi.fluxo_ut."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    diff = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut f WHERE NOT EXISTS (SELECT 1 FROM kpi.validacao_nota v WHERE v.ut_id = f.ut_id)",
    )
    assert diff == 0, f"{diff} UTs em fluxo_ut sem linha em validacao_nota"


# ===========================================================================
# 5. kpi.pontos_usuario
# ===========================================================================

_CAMPOS_PONTOS = {"ut_id", "projeto_id", "subfase_id", "usuario_id", "usuario_nome", "papel", "pontos", "percentual_dos_pontos"}


def test_pontos_usuario_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    ausentes = _CAMPOS_PONTOS - _colunas(engine_cp, "kpi", "pontos_usuario")
    assert not ausentes, f"Campos ausentes em kpi.pontos_usuario: {ausentes}"


def test_pontos_usuario_apenas_para_concluidas(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Pontos só existem para UTs com fluxo fechado e nota válida."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    orphans = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.pontos_usuario pu "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM kpi.validacao_fluxo vf "
        "  JOIN kpi.validacao_nota vn ON vn.ut_id = vf.ut_id "
        "  WHERE vf.ut_id = pu.ut_id AND vf.fluxo_fechado = TRUE AND vn.nota_valida = TRUE"
        ")",
    )
    assert orphans == 0, f"{orphans} linhas em pontos_usuario para UTs não concluídas"


def test_pontos_usuario_pontos_nao_negativos(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.pontos_usuario WHERE pontos < 0",
    )
    assert violacoes == 0, f"{violacoes} linhas com pontos negativos"


def test_pontos_usuario_soma_igual_dificuldade(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Para UTs concluídas, soma de pontos por UT = dificuldade da UT."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM ("
        "  SELECT pu.ut_id, SUM(pu.pontos) AS soma, f.ut_dificuldade "
        "  FROM kpi.pontos_usuario pu "
        "  JOIN kpi.fluxo_ut f ON f.ut_id = pu.ut_id "
        "  GROUP BY pu.ut_id, f.ut_dificuldade "
        "  HAVING ABS(SUM(pu.pontos) - f.ut_dificuldade) > 0.01"
        ") x",
    )
    assert violacoes == 0, f"{violacoes} UTs onde soma de pontos difere da dificuldade"


def test_pontos_usuario_papeis_validos(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    papeis = {r["papel"] for r in _buscar(engine_cp, "SELECT DISTINCT papel FROM kpi.pontos_usuario")}
    invalidos = papeis - {"EXECUTOR", "REVISOR", "CORRETOR"}
    assert not invalidos, f"Papéis inválidos em kpi.pontos_usuario: {invalidos}"


def test_pontos_usuario_ciclos_sem_nota_somente_executor_revisor(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Ciclos 3 e 4 não têm CORRETOR em pontos_usuario."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.pontos_usuario pu "
        "JOIN kpi.fluxo_ut f ON f.ut_id = pu.ut_id "
        "WHERE f.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL') "
        "AND pu.papel = 'CORRETOR'",
    )
    assert violacoes == 0, f"{violacoes} linhas CORRETOR em ciclos sem correção"


# ===========================================================================
# 6. kpi.estado_ut
# ===========================================================================

_CAMPOS_ESTADO_UT = {
    "ut_id",
    "ciclo_modelo",
    "estado_ut_subfase",
    "concluida",
    "projeto_nome",
    "lote_nome",
    "bloco_nome",
    "fase_nome",
    "subfase_nome",
    "ut_disponivel",
    "ut_dificuldade",
    "nota_qualidade",
    "texto_qualidade",
    "ocorrencia",
    "percentual_producao_revisor",
    "percentual_producao_executor",
    "usuario_executor_nome",
    "usuario_executor_exibicao",
    "executor_tipo_situacao_id",
    "executor_tipo_situacao_nome",
    "usuario_revisor_nome",
    "revisao_vigente_tipo_situacao_id",
    "revisao_vigente_tipo_situacao_nome",
    "usuario_corretor_nome",
    "corretor_tipo_situacao_nome",
    "total_atividades",
    "total_finalizadas",
    "total_nao_finalizadas",
    "total_pendentes",
    "possui_nao_finalizada_no_historico",
    "observacoes_concatenadas",
    "data_inicio_fluxo",
    "data_fim_fluxo",
}


def test_estado_ut_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    ausentes = _CAMPOS_ESTADO_UT - _colunas(engine_cp, "kpi", "estado_ut")
    assert not ausentes, f"Campos ausentes em kpi.estado_ut: {ausentes}"


def test_estado_ut_estados_validos(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    estados = {r["estado_ut_subfase"] for r in _buscar(engine_cp, "SELECT DISTINCT estado_ut_subfase FROM kpi.estado_ut")}
    invalidos = estados - _ESTADOS_VALIDOS
    assert not invalidos, f"estado_ut_subfase inválido: {invalidos}"


def test_estado_ut_cobertura_total(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """kpi.estado_ut deve cobrir todas as UTs de kpi.fluxo_ut."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    diff = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut f WHERE NOT EXISTS (SELECT 1 FROM kpi.estado_ut e WHERE e.ut_id = f.ut_id)",
    )
    assert diff == 0, f"{diff} UTs em fluxo_ut sem linha em estado_ut"


def test_estado_ut_concluida_implica_fluxo_fechado(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """estado_ut.concluida=TRUE deve corresponder a fluxo_fechado=TRUE e nota_valida=TRUE."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.estado_ut e "
        "JOIN kpi.validacao_fluxo vf ON vf.ut_id = e.ut_id "
        "JOIN kpi.validacao_nota  vn ON vn.ut_id = e.ut_id "
        "WHERE e.concluida = TRUE AND (vf.fluxo_fechado = FALSE OR vn.nota_valida = FALSE)",
    )
    assert violacoes == 0, f"{violacoes} UTs marcadas concluida=TRUE mas fluxo aberto ou nota inválida"


def test_estado_ut_nao_concluida_implica_estado_correto(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """concluida=FALSE nunca tem estado CONCLUIDA_*."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.estado_ut WHERE concluida = FALSE AND estado_ut_subfase LIKE 'CONCLUIDA%'",
    )
    assert violacoes == 0, f"{violacoes} UTs com concluida=FALSE mas estado CONCLUIDA_*"


def test_estado_ut_pontos_somente_para_concluidas(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Só UTs concluídas existem em kpi.pontos_usuario."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.pontos_usuario pu LEFT JOIN kpi.estado_ut e ON e.ut_id = pu.ut_id WHERE e.concluida IS DISTINCT FROM TRUE",
    )
    assert violacoes == 0, f"{violacoes} linhas de pontos para UTs não concluídas"


def test_estado_ut_inconsistente_nota_auditavel(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Para UTs INCONSISTENTE_NOTA, validacao_nota deve ter nota_valida=FALSE e motivo preenchido."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    inconsistentes = _buscar(
        engine_cp,
        "SELECT e.ut_id FROM kpi.estado_ut e WHERE e.estado_ut_subfase = 'INCONSISTENTE_NOTA'",
    )
    if not inconsistentes:
        pytest.skip("Seed não produziu UTs INCONSISTENTE_NOTA para este cenário")

    for row in inconsistentes:
        nota = _buscar(
            engine_cp,
            "SELECT nota_valida, ocorrencia FROM kpi.validacao_nota WHERE ut_id = :uid",
            {"uid": row["ut_id"]},
        )
        assert nota, f"ut_id={row['ut_id']} INCONSISTENTE_NOTA sem linha em validacao_nota"
        assert nota[0]["nota_valida"] is False, f"ut_id={row['ut_id']}: INCONSISTENTE_NOTA mas nota_valida=TRUE"
        assert nota[0]["ocorrencia"] in ("NOTA_AUSENTE", "NOTA_INVALIDA"), f"ut_id={row['ut_id']}: ocorrencia inesperada: {nota[0]['ocorrencia']}"


def test_estado_ut_bloqueada_auditavel(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Para UTs UT BLOQUEADA, fluxo_ut.ut_disponivel deve ser FALSE."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.estado_ut e "
        "JOIN kpi.fluxo_ut f ON f.ut_id = e.ut_id "
        "WHERE e.estado_ut_subfase = 'UT BLOQUEADA' AND f.ut_disponivel IS DISTINCT FROM FALSE",
    )
    assert violacoes == 0, f"{violacoes} UTs 'UT BLOQUEADA' com ut_disponivel <> FALSE"


def test_estado_ut_idempotente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    c1 = _scalar(engine_cp, "SELECT COUNT(*) FROM kpi.estado_ut")
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    c2 = _scalar(engine_cp, "SELECT COUNT(*) FROM kpi.estado_ut")
    assert c1 == c2, f"kpi.estado_ut instável entre syncs: {c1} → {c2}"


# ===========================================================================
# 7. Rastreabilidade cross-table
#    Testa que é possível auditar cada decisão consultando as tabelas certas
# ===========================================================================


def test_rastreabilidade_pendente_execucao(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """PENDENTE_EXECUCAO: validacao_fluxo.etapa_bloqueante = 'EXECUTOR'."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.estado_ut e "
        "JOIN kpi.validacao_fluxo vf ON vf.ut_id = e.ut_id "
        "WHERE e.estado_ut_subfase = 'PENDENTE_EXECUCAO' "
        "AND vf.etapa_bloqueante <> 'EXECUTOR'",
    )
    assert violacoes == 0, f"{violacoes} UTs PENDENTE_EXECUCAO com etapa_bloqueante errada"


def test_rastreabilidade_pendente_revisao(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """PENDENTE_REVISAO: validacao_fluxo.etapa_bloqueante = 'REVISAO'."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.estado_ut e "
        "JOIN kpi.validacao_fluxo vf ON vf.ut_id = e.ut_id "
        "WHERE e.estado_ut_subfase = 'PENDENTE_REVISAO' "
        "AND vf.etapa_bloqueante <> 'REVISAO'",
    )
    assert violacoes == 0, f"{violacoes} UTs PENDENTE_REVISAO com etapa_bloqueante errada"


def test_rastreabilidade_concluida_pontos_existem(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Toda UT concluída deve ter pelo menos 2 linhas em pontos_usuario (executor + revisor)."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.estado_ut e WHERE e.concluida = TRUE AND (SELECT COUNT(*) FROM kpi.pontos_usuario pu WHERE pu.ut_id = e.ut_id) < 2",
    )
    assert violacoes == 0, f"{violacoes} UTs concluídas com menos de 2 linhas em pontos_usuario"


# ===========================================================================
# 7. kpi.distribuicao_pontos
# ===========================================================================

_CAMPOS_DISTRIBUICAO = {
    "projeto_nome",
    "subfase_nome",
    "ut_id",
    "pontos_ut",
    "ciclo_modelo",
<<<<<<< HEAD
    "nota",
=======
    "nota_final",
>>>>>>> feature/front
    "nota_valida",
    "nome_executor",
    "pontos_executor",
    "nome_corretor",
    "pontos_corretor",
    "nome_revisor",
    "pontos_revisor",
}


def test_distribuicao_pontos_tem_campos_obrigatorios(engine_cp: Engine) -> None:
    ausentes = _CAMPOS_DISTRIBUICAO - _colunas(engine_cp, "kpi", "distribuicao_pontos")
    assert not ausentes, f"Campos ausentes em kpi.distribuicao_pontos: {ausentes}"


def test_distribuicao_pontos_somente_para_concluidas(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Toda UT em distribuicao_pontos deve estar concluída em estado_ut."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    orphans = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.distribuicao_pontos dp "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM kpi.estado_ut e "
        "  WHERE e.ut_id = dp.ut_id AND e.concluida = TRUE"
        ")",
    )
    assert orphans == 0, f"{orphans} UTs em distribuicao_pontos sem concluida=TRUE em estado_ut"


def test_distribuicao_pontos_executor_sempre_presente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Toda linha em distribuicao_pontos tem pontos_executor preenchido."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.distribuicao_pontos WHERE pontos_executor IS NULL",
    )
    assert violacoes == 0, f"{violacoes} UTs em distribuicao_pontos sem pontos_executor"


def test_distribuicao_pontos_soma_consistente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """pontos_executor + COALESCE(pontos_corretor,0) + pontos_revisor ≈ pontos_ut."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.distribuicao_pontos "
        "WHERE ABS("
        "  COALESCE(pontos_executor, 0) + "
        "  COALESCE(pontos_corretor, 0) + "
        "  COALESCE(pontos_revisor, 0) - "
        "  COALESCE(pontos_ut, 0)"
        ") > 0.01",
    )
    assert violacoes == 0, f"{violacoes} UTs com soma de pontos divergente de pontos_ut"


def test_distribuicao_pontos_nota_valida_correto(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """nota_valida em distribuicao_pontos deve bater com validacao_nota."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.distribuicao_pontos dp JOIN kpi.validacao_nota vn ON vn.ut_id = dp.ut_id WHERE dp.nota_valida <> vn.nota_valida",
    )
    assert violacoes == 0, f"{violacoes} divergências de nota_valida entre distribuicao_pontos e validacao_nota"


# ===========================================================================
# 8. Invariantes cross-table adicionais
# ===========================================================================


def test_data_fim_fluxo_null_quando_nao_concluida(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """fluxo_ut.data_fim_fluxo deve ser NULL para UTs com fluxo não fechado."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut f "
        "JOIN kpi.validacao_fluxo vf ON vf.ut_id = f.ut_id "
        "WHERE vf.fluxo_fechado = FALSE AND f.data_fim_fluxo IS NOT NULL",
    )
    assert violacoes == 0, f"{violacoes} UTs com fluxo aberto mas data_fim_fluxo preenchida"


def test_data_fim_fluxo_preenchida_quando_concluida(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """fluxo_ut.data_fim_fluxo deve estar preenchida para UTs com fluxo fechado."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.fluxo_ut f "
        "JOIN kpi.validacao_fluxo vf ON vf.ut_id = f.ut_id "
        "WHERE vf.fluxo_fechado = TRUE AND f.data_fim_fluxo IS NULL",
    )
    assert violacoes == 0, f"{violacoes} UTs com fluxo fechado mas data_fim_fluxo NULL"


def test_ocorrencia_distribuicao_default_ciclos_sem_nota(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Ciclos 3 e 4 sempre têm ocorrencia = DISTRIBUICAO_DEFAULT."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_nota "
        "WHERE ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL') "
        "AND ocorrencia <> 'DISTRIBUICAO_DEFAULT'",
    )
    assert violacoes == 0, f"{violacoes} ciclos sem nota com ocorrencia <> DISTRIBUICAO_DEFAULT"


def test_ocorrencia_nota_valida_quando_nota_ok(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Quando nota entre 1-9, ocorrencia = NOTA_VALIDA."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.validacao_nota WHERE nota_qualidade BETWEEN 1 AND 9 AND ocorrencia <> 'NOTA_VALIDA'",
    )
    assert violacoes == 0, f"{violacoes} UTs com nota válida mas ocorrencia <> NOTA_VALIDA"


def test_pontos_usuario_tem_percentual_dos_pontos(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """percentual_dos_pontos deve estar preenchido para EXECUTOR e REVISOR."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    violacoes = _scalar(
        engine_cp,
        "SELECT COUNT(*) FROM kpi.pontos_usuario WHERE papel IN ('EXECUTOR', 'REVISOR') AND percentual_dos_pontos IS NULL",
    )
    assert violacoes == 0, f"{violacoes} linhas EXECUTOR/REVISOR sem percentual_dos_pontos"
