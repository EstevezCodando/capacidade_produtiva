"""DDL das views analíticas do schema sap_analytics.

Camada de consumo construída sobre sap_snapshot.
As views são recriadas via DROP ... CASCADE + CREATE a cada aplicação,
garantindo que mudanças de assinatura (novas colunas, reordenação) nunca
causem InvalidTableDefinition no PostgreSQL.

Views disponíveis:
  - vw_ut_enriquecida        : UT com toda hierarquia (projeto → lote → bloco → subfase → fase)
  - vw_atividade_enriquecida : atividade com etapa, tipo_etapa, tipo_situacao, usuario, flag is_finalizada
  - vw_ut_atividade          : join completo UT + atividade (critério 4 do sprint)
  - vw_ut_subfase_conclusao  : agregação (ut, subfase) → conclusão real baseada em todas as atividades

Regra de conclusão de (ut, subfase):
  Uma unidade de trabalho está concluída em uma subfase quando TODAS as suas atividades
  naquela subfase têm tipo_situacao_id IN (4=Finalizada, 5=Não finalizada).
  Qualquer atividade em 1=Não iniciada, 2=Em execução ou 3=Pausada impede a conclusão.
"""

from __future__ import annotations

_SCHEMA_ANALYTICS = "sap_analytics"
_SCHEMA_SNAPSHOT = "sap_snapshot"

# ---------------------------------------------------------------------------
# DDL — schema
# ---------------------------------------------------------------------------

DDL_SCHEMA = f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA_ANALYTICS};"

# ---------------------------------------------------------------------------
# DDL — vw_ut_enriquecida
#
# Hierarquia completa da Unidade de Trabalho:
#   ut → subfase → fase → tipo_fase (fase_nome)
#   ut → lote → projeto
#   ut → bloco
# ---------------------------------------------------------------------------

DDL_VW_UT_ENRIQUECIDA = f"""
CREATE VIEW {_SCHEMA_ANALYTICS}.vw_ut_enriquecida AS
SELECT
    -- Projeto
    proj.id          AS projeto_id,
    proj.nome        AS projeto_nome,

    -- Lote
    lote.id          AS lote_id,
    lote.nome        AS lote_nome,

    -- Bloco
    bloco.id         AS bloco_id,
    bloco.nome       AS bloco_nome,

    -- Subfase
    sf.id            AS subfase_id,
    sf.nome          AS subfase_nome,

    -- Fase (tipo_fase fornece o nome legível)
    fase.id          AS fase_id,
    tf.nome          AS fase_nome,

    -- Unidade de Trabalho
    ut.id            AS ut_id,
    ut.nome          AS ut_nome,
    ut.dificuldade,
    ut.tempo_estimado_minutos

FROM {_SCHEMA_SNAPSHOT}.macrocontrole_unidade_trabalho  AS ut
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_subfase           AS sf    ON sf.id    = ut.subfase_id
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_fase              AS fase  ON fase.id  = sf.fase_id
JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_fase               AS tf    ON tf.code  = fase.tipo_fase_id
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_lote              AS lote  ON lote.id  = ut.lote_id
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_projeto           AS proj  ON proj.id  = lote.projeto_id
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_bloco             AS bloco ON bloco.id = ut.bloco_id;
""".strip()

# ---------------------------------------------------------------------------
# DDL — vw_atividade_enriquecida
#
# Atividade com toda informação dimensional resolvida:
#   atividade → etapa → tipo_etapa
#   atividade → tipo_situacao
#   atividade → usuario (dgeo)
#   is_finalizada: tipo_situacao_id = 4 (Finalizada)
# ---------------------------------------------------------------------------

DDL_VW_ATIVIDADE_ENRIQUECIDA = f"""
CREATE VIEW {_SCHEMA_ANALYTICS}.vw_atividade_enriquecida AS
SELECT
    -- Atividade
    atv.id              AS atividade_id,
    atv.unidade_trabalho_id,

    -- Etapa
    etapa.id            AS etapa_id,

    -- Tipo de etapa
    te.code             AS tipo_etapa_id,
    te.nome             AS tipo_etapa_nome,

    -- Tipo de situação
    ts.code             AS tipo_situacao_id,
    ts.nome             AS tipo_situacao_nome,

    -- Usuário
    usr.id              AS usuario_id,
    usr.nome            AS usuario_nome,

    -- Temporais
    atv.data_inicio,
    atv.data_fim,

    -- Texto livre
    atv.observacao,

    -- Flag derivada: finalizada somente quando tipo_situacao_id = 4
    (atv.tipo_situacao_id = 4) AS is_finalizada

FROM {_SCHEMA_SNAPSHOT}.macrocontrole_atividade         AS atv
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_etapa             AS etapa ON etapa.id   = atv.etapa_id
JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_etapa              AS te    ON te.code    = etapa.tipo_etapa_id
JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_situacao           AS ts    ON ts.code    = atv.tipo_situacao_id
LEFT JOIN {_SCHEMA_SNAPSHOT}.dgeo_usuario               AS usr   ON usr.id     = atv.usuario_id;
""".strip()

# ---------------------------------------------------------------------------
# DDL — vw_ut_atividade
#
# Join completo conforme critério 4 do sprint:
#   lote_id/nome, bloco_id/nome, subfase_id/nome, ut_nome, dificuldade,
#   atividade_id, tipo_etapa_id/nome, tipo_situacao_id/nome,
#   usuario_id/nome, observação, is_finalizada, data_inicio, data_fim
# ---------------------------------------------------------------------------

DDL_VW_UT_ATIVIDADE = f"""
CREATE VIEW {_SCHEMA_ANALYTICS}.vw_ut_atividade AS
SELECT
    -- Hierarquia da UT
    ut_enr.projeto_id,
    ut_enr.projeto_nome,
    ut_enr.lote_id,
    ut_enr.lote_nome,
    ut_enr.bloco_id,
    ut_enr.bloco_nome,
    ut_enr.subfase_id,
    ut_enr.subfase_nome,
    ut_enr.fase_id,
    ut_enr.fase_nome,
    ut_enr.ut_id,
    ut_enr.ut_nome,
    ut_enr.dificuldade,
    ut_enr.tempo_estimado_minutos,

    -- Atividade
    atv_enr.atividade_id,
    atv_enr.etapa_id,
    atv_enr.tipo_etapa_id,
    atv_enr.tipo_etapa_nome,
    atv_enr.tipo_situacao_id,
    atv_enr.tipo_situacao_nome,
    atv_enr.usuario_id,
    atv_enr.usuario_nome,
    atv_enr.observacao,
    atv_enr.is_finalizada,
    atv_enr.data_inicio,
    atv_enr.data_fim

FROM {_SCHEMA_ANALYTICS}.vw_ut_enriquecida          AS ut_enr
JOIN {_SCHEMA_ANALYTICS}.vw_atividade_enriquecida   AS atv_enr
    ON atv_enr.unidade_trabalho_id = ut_enr.ut_id;
""".strip()

# ---------------------------------------------------------------------------
# DDL — vw_ut_subfase_conclusao
#
# Agrega todas as atividades por (ut, subfase) e deriva se o par está concluído.
#
# Regra de negócio:
#   concluida = TRUE  → todas as atividades têm situacao IN (4, 5)
#   concluida = FALSE → existe ao menos uma atividade em (1, 2 ou 3)
#
# Situações que BLOQUEIAM a conclusão:
#   1 = Não iniciada
#   2 = Em execução
#   3 = Pausada
#
# Situações que PERMITEM a conclusão:
#   4 = Finalizada
#   5 = Não finalizada  (encerrada por decisão, não por conclusão normal)
#
# Campos de observabilidade:
#   total_atividades   — total de atividades do par (ut, subfase)
#   total_concluidas   — situacao IN (4, 5)
#   total_pendentes    — situacao IN (1, 2, 3) — devem ser 0 para concluir
#   etapas_situacao    — array ordenado com "TipoEtapa: Situação" para TODAS as etapas
#                        ex: ["Execução: Não iniciada", "Revisão: Finalizada"]
#   situacoes_pendentes — array com "TipoEtapa: Situação" apenas das que bloqueiam
#                        ex: ["Execução: Não iniciada", "Revisão: Pausada"]
# ---------------------------------------------------------------------------

DDL_VW_UT_SUBFASE_CONCLUSAO = f"""
CREATE VIEW {_SCHEMA_ANALYTICS}.vw_ut_subfase_conclusao AS
WITH atividades_por_ut_subfase AS (
    SELECT
        atv.unidade_trabalho_id                                      AS ut_id,
        etapa.subfase_id,

        -- Contagens por categoria de situação
        COUNT(*)                                                      AS total_atividades,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id IN (4, 5))       AS total_concluidas,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id IN (1, 2, 3))    AS total_pendentes,

        -- Todas as etapas com sua situação atual, ordenadas por tipo_etapa
        -- Formato: "TipoEtapa: Situação" ex: "Execução: Finalizada"
        ARRAY_REMOVE(
            ARRAY_AGG(
                te.nome || ': ' || ts.nome
                ORDER BY te.nome, ts.nome
            ),
            NULL
        )                                                             AS etapas_situacao,

        -- Apenas as combinações que ainda bloqueiam (situacao IN 1, 2, 3)
        -- Formato: "TipoEtapa: Situação" ex: "Execução: Não iniciada"
        ARRAY_REMOVE(
            ARRAY_AGG(
                CASE
                    WHEN atv.tipo_situacao_id IN (1, 2, 3)
                    THEN te.nome || ': ' || ts.nome
                END
                ORDER BY te.nome, ts.nome
            ),
            NULL
        )                                                             AS situacoes_pendentes,

                -- Diagnóstico: concatena todas as observações lançadas (ordem estável)
        STRING_AGG(
            CASE
                WHEN atv.observacao IS NOT NULL AND BTRIM(atv.observacao) <> ''
                THEN te.nome || ': ' || ts.nome || ' -> ' ||
                     REGEXP_REPLACE(BTRIM(atv.observacao), '\\s+', ' ', 'g')
            END,
            ' | '
            ORDER BY te.nome, atv.id
        )                                                             AS observacoes_concatenadas,

        -- Conclusão real: nenhuma atividade pendente
        BOOL_AND(atv.tipo_situacao_id IN (4, 5))                     AS concluida

    FROM {_SCHEMA_SNAPSHOT}.macrocontrole_atividade  AS atv
    JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_etapa      AS etapa ON etapa.id   = atv.etapa_id
    JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_situacao    AS ts    ON ts.code    = atv.tipo_situacao_id
    JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_etapa       AS te    ON te.code    = etapa.tipo_etapa_id
    GROUP BY atv.unidade_trabalho_id, etapa.subfase_id
)
SELECT
    -- Identificadores
    agg.ut_id,
    ut.nome                 AS ut_nome,
    agg.subfase_id,
    sf.nome                 AS subfase_nome,

    -- Hierarquia para facilitar filtros downstream
    lote.id                 AS lote_id,
    lote.nome               AS lote_nome,
    bloco.id                AS bloco_id,
    bloco.nome              AS bloco_nome,
    fase.id                 AS fase_id,
    tf.nome                 AS fase_nome,
    proj.id                 AS projeto_id,
    proj.nome               AS projeto_nome,

    -- Métricas de atividades
    agg.total_atividades,
    agg.total_concluidas,
    agg.total_pendentes,
    -- Diagnostico das notas:
        agg.observacoes_concatenadas,

    -- Diagnóstico completo: todas as etapas com sua situação
    agg.etapas_situacao,

    -- Diagnóstico de bloqueio: apenas etapas que impedem conclusão
    agg.situacoes_pendentes,

    -- Flag principal
    agg.concluida

FROM atividades_por_ut_subfase                              AS agg
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_unidade_trabalho     AS ut    ON ut.id    = agg.ut_id
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_subfase              AS sf    ON sf.id    = agg.subfase_id
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_fase                 AS fase  ON fase.id  = sf.fase_id
JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_fase                  AS tf    ON tf.code  = fase.tipo_fase_id
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_lote                 AS lote  ON lote.id  = ut.lote_id
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_projeto              AS proj  ON proj.id  = lote.projeto_id
JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_bloco                AS bloco ON bloco.id = ut.bloco_id;
""".strip()

# ---------------------------------------------------------------------------
# Conjunto ordenado de DDLs (dependências respeitadas para CREATE)
# ---------------------------------------------------------------------------

TODAS_AS_VIEWS: tuple[str, ...] = (
    DDL_VW_UT_ENRIQUECIDA,
    DDL_VW_ATIVIDADE_ENRIQUECIDA,
    DDL_VW_UT_ATIVIDADE,  # depende das duas anteriores
    DDL_VW_UT_SUBFASE_CONCLUSAO,  # agregação independente sobre sap_snapshot
)

# Ordem inversa para DROP CASCADE (dependentes primeiro)
NOMES_DAS_VIEWS: tuple[str, ...] = (
    f"{_SCHEMA_ANALYTICS}.vw_ut_subfase_conclusao",
    f"{_SCHEMA_ANALYTICS}.vw_ut_atividade",
    f"{_SCHEMA_ANALYTICS}.vw_atividade_enriquecida",
    f"{_SCHEMA_ANALYTICS}.vw_ut_enriquecida",
)
