"""DDL e SQL das 7 tabelas materializadas do schema kpi.

Cadeia de dependências (ordem estrita de materialização):

  sap_snapshot
      │
      ▼
  kpi.fluxo_ut           ← ciclo detectado + atividades vigentes (pivot)
      │
      ▼
  kpi.participantes_ut   ← participantes normalizados por papel
      │
      ▼
  kpi.validacao_fluxo    ← fluxo fechado / etapa bloqueante
      │
      ▼
  kpi.validacao_nota     ← nota extraída, validada, ocorrência classificada
      │
      ▼
  kpi.pontos_usuario     ← pontos calculados por (ut, usuário, papel)
      │
      ▼
  kpi.estado_ut          ← estado consolidado + datas corretas
      │
      ▼
  kpi.distribuicao_pontos ← visão wide desnormalizada para BI/API

Ciclos suportados:
  CICLO_1_PADRAO            : Exec(1) → Rev(2) → Cor(3)               nota na Cor
  CICLO_2_REVISAO_CORRECAO  : Exec(1) → RevCor(4)                     nota na RevCor
  CICLO_3_SEM_CORRECAO      : Exec(1) → Rev(2)                        sem nota
  CICLO_4_REVISAO_FINAL     : Exec(1) → [Rev(2) →] [Cor(3) →] RevFinal(5)  sem nota

ATENÇÃO — bug de NULL em SQL:
  NULL BETWEEN 1 AND 9  →  NULL  (não FALSE)
  NOT (NULL BETWEEN 1 AND 9)  →  NULL  (não TRUE)
  Sempre usar: COALESCE(expr BETWEEN 1 AND 9, FALSE)
  ou: expr IS NULL OR expr NOT BETWEEN 1 AND 9
"""

from __future__ import annotations

_S = "sap_snapshot"
_K = "kpi"

# ===========================================================================
# CTEs compartilhados — embutidos como strings, compostos nos SELECTs
# ===========================================================================

_CTE_UT_BASE = f"""
ut_base AS (
    SELECT
        ut.id                                                  AS ut_id,
        ut.lote_id,
        ut.bloco_id,
        ut.subfase_id,
        ut.dificuldade                                         AS ut_dificuldade,
        ut.disponivel                                          AS ut_disponivel,
        lote.nome                                              AS lote_nome,
        bloco.nome                                             AS bloco_nome,
        sf.nome                                                AS subfase_nome,
        fase.id                                                AS fase_id,
        tf.nome                                                AS fase_nome,
        proj.id                                                AS projeto_id,
        proj.nome                                              AS projeto_nome
    FROM {_S}.macrocontrole_unidade_trabalho ut
    JOIN {_S}.macrocontrole_lote lote   ON lote.id  = ut.lote_id
    JOIN {_S}.macrocontrole_bloco bloco ON bloco.id = ut.bloco_id
    JOIN {_S}.macrocontrole_subfase sf  ON sf.id    = ut.subfase_id
    JOIN {_S}.macrocontrole_fase fase   ON fase.id  = sf.fase_id
    JOIN {_S}.dominio_tipo_fase tf      ON tf.code  = fase.tipo_fase_id
    JOIN {_S}.macrocontrole_projeto proj ON proj.id = lote.projeto_id
)""".strip()

_CTE_ETAPA_CANONICA = f"""
etapa_com_min_ordem AS (
    SELECT
        e.id                                                   AS etapa_id,
        e.lote_id,
        e.subfase_id,
        e.tipo_etapa_id,
        e.ordem,
        MIN(e.ordem) OVER (
            PARTITION BY e.lote_id, e.subfase_id, e.tipo_etapa_id
        )                                                      AS min_ordem
    FROM {_S}.macrocontrole_etapa e
),
etapa_ordenada AS (
    SELECT
        emo.etapa_id,
        emo.lote_id,
        emo.subfase_id,
        emo.tipo_etapa_id,
        emo.ordem,
        ROW_NUMBER() OVER (
            PARTITION BY emo.lote_id, emo.subfase_id, emo.tipo_etapa_id
            ORDER BY emo.ordem, emo.etapa_id
        )                                                      AS rn,
        COUNT(*) FILTER (WHERE emo.ordem = emo.min_ordem) OVER (
            PARTITION BY emo.lote_id, emo.subfase_id, emo.tipo_etapa_id
        )                                                      AS qtd_menor_ordem
    FROM etapa_com_min_ordem emo
),
etapa_canonica AS (
    SELECT
        eo.lote_id,
        eo.subfase_id,
        eo.tipo_etapa_id,
        eo.etapa_id,
        (eo.qtd_menor_ordem > 1)                               AS etapa_canonica_ambigua
    FROM etapa_ordenada eo
    WHERE eo.rn = 1
)""".strip()

_CTE_ATIVIDADE_VIGENTE = f"""
atividade_historico AS (
    SELECT
        atv.id                                                 AS atividade_id,
        atv.unidade_trabalho_id                                AS ut_id,
        ub.subfase_id,
        ub.lote_id,
        ec.tipo_etapa_id,
        atv.etapa_id,
        atv.usuario_id,
        atv.tipo_situacao_id,
        ts.nome                                                AS tipo_situacao_nome,
        te.nome                                                AS tipo_etapa_nome,
        atv.data_inicio,
        atv.data_fim,
        atv.observacao,
        ec.etapa_canonica_ambigua
    FROM {_S}.macrocontrole_atividade atv
    JOIN ut_base ub
      ON ub.ut_id = atv.unidade_trabalho_id
    JOIN etapa_canonica ec
      ON ec.etapa_id   = atv.etapa_id
     AND ec.lote_id    = ub.lote_id
     AND ec.subfase_id = ub.subfase_id
    JOIN {_S}.dominio_tipo_situacao ts ON ts.code = atv.tipo_situacao_id
    JOIN {_S}.dominio_tipo_etapa te    ON te.code = ec.tipo_etapa_id
),
atividade_vigente AS (
    SELECT *
    FROM (
        SELECT
            ah.*,
            ROW_NUMBER() OVER (
                PARTITION BY ah.ut_id, ah.subfase_id, ah.tipo_etapa_id
                ORDER BY ah.atividade_id DESC
            )                                                  AS rn
        FROM atividade_historico ah
    ) x
    WHERE x.rn = 1
)""".strip()

_CTE_PIVOT_VIGENTE = """
pivot_vigente AS (
    SELECT
        av.ut_id,
        av.subfase_id,

        MAX(CASE WHEN av.tipo_etapa_id = 1 THEN av.atividade_id END)        AS exec_atividade_id,
        MAX(CASE WHEN av.tipo_etapa_id = 1 THEN av.usuario_id END)          AS exec_usuario_id,
        MAX(CASE WHEN av.tipo_etapa_id = 1 THEN av.tipo_situacao_id END)    AS exec_tipo_situacao_id,
        MAX(CASE WHEN av.tipo_etapa_id = 1 THEN av.tipo_situacao_nome END)  AS exec_tipo_situacao_nome,
        BOOL_OR(CASE WHEN av.tipo_etapa_id = 1 THEN av.etapa_canonica_ambigua ELSE FALSE END) AS exec_ambigua,

        MAX(CASE WHEN av.tipo_etapa_id = 2 THEN av.atividade_id END)        AS rev_atividade_id,
        MAX(CASE WHEN av.tipo_etapa_id = 2 THEN av.usuario_id END)          AS rev_usuario_id,
        MAX(CASE WHEN av.tipo_etapa_id = 2 THEN av.tipo_situacao_id END)    AS rev_tipo_situacao_id,
        MAX(CASE WHEN av.tipo_etapa_id = 2 THEN av.tipo_situacao_nome END)  AS rev_tipo_situacao_nome,
        BOOL_OR(CASE WHEN av.tipo_etapa_id = 2 THEN av.etapa_canonica_ambigua ELSE FALSE END) AS rev_ambigua,

        MAX(CASE WHEN av.tipo_etapa_id = 3 THEN av.atividade_id END)        AS cor_atividade_id,
        MAX(CASE WHEN av.tipo_etapa_id = 3 THEN av.usuario_id END)          AS cor_usuario_id,
        MAX(CASE WHEN av.tipo_etapa_id = 3 THEN av.tipo_situacao_id END)    AS cor_tipo_situacao_id,
        MAX(CASE WHEN av.tipo_etapa_id = 3 THEN av.tipo_situacao_nome END)  AS cor_tipo_situacao_nome,
        MAX(CASE WHEN av.tipo_etapa_id = 3 THEN av.observacao END)          AS cor_observacao,
        BOOL_OR(CASE WHEN av.tipo_etapa_id = 3 THEN av.etapa_canonica_ambigua ELSE FALSE END) AS cor_ambigua,

        MAX(CASE WHEN av.tipo_etapa_id = 4 THEN av.atividade_id END)        AS revcor_atividade_id,
        MAX(CASE WHEN av.tipo_etapa_id = 4 THEN av.usuario_id END)          AS revcor_usuario_id,
        MAX(CASE WHEN av.tipo_etapa_id = 4 THEN av.tipo_situacao_id END)    AS revcor_tipo_situacao_id,
        MAX(CASE WHEN av.tipo_etapa_id = 4 THEN av.tipo_situacao_nome END)  AS revcor_tipo_situacao_nome,
        MAX(CASE WHEN av.tipo_etapa_id = 4 THEN av.observacao END)          AS revcor_observacao,
        BOOL_OR(CASE WHEN av.tipo_etapa_id = 4 THEN av.etapa_canonica_ambigua ELSE FALSE END) AS revcor_ambigua,

        MAX(CASE WHEN av.tipo_etapa_id = 5 THEN av.atividade_id END)        AS revfinal_atividade_id,
        MAX(CASE WHEN av.tipo_etapa_id = 5 THEN av.usuario_id END)          AS revfinal_usuario_id,
        MAX(CASE WHEN av.tipo_etapa_id = 5 THEN av.tipo_situacao_id END)    AS revfinal_tipo_situacao_id,
        MAX(CASE WHEN av.tipo_etapa_id = 5 THEN av.tipo_situacao_nome END)  AS revfinal_tipo_situacao_nome,
        BOOL_OR(CASE WHEN av.tipo_etapa_id = 5 THEN av.etapa_canonica_ambigua ELSE FALSE END) AS revfinal_ambigua

    FROM atividade_vigente av
    GROUP BY av.ut_id, av.subfase_id
)""".strip()


# ===========================================================================
# Tabela 1 — kpi.fluxo_ut
#
# data_inicio_fluxo : MIN(data_inicio) de todas as atividades — sempre presente
# data_fim_fluxo    : MAX(data_fim) SOMENTE quando o fluxo está concluído
#                     (todas etapas finalizadas + somente_finalizada_ou_nao_finalizada)
#                     NULL enquanto qualquer etapa estiver pendente.
#
# O fluxo fechado é calculado inline para não depender de kpi.validacao_fluxo
# (que ainda não existe neste ponto da cadeia).
# ===========================================================================

DDL_FLUXO_UT = f"""
CREATE TABLE IF NOT EXISTS {_K}.fluxo_ut (
    projeto_id                  integer,
    projeto_nome                text        NOT NULL,
    lote_nome                   text        NOT NULL,
    bloco_nome                  text        NOT NULL,
    fase_nome                   text        NOT NULL,
    subfase_id                  integer,
    subfase_nome                text        NOT NULL,
    ut_id                       integer     NOT NULL,
    ut_disponivel               boolean,
    ut_dificuldade              numeric,

    -- Atividade de execução (tipo_etapa_id = 1)
    exec_atividade_id           integer,
    exec_usuario_id             integer,
    exec_tipo_situacao_id       integer,
    exec_tipo_situacao_nome     text,

    -- Atividade de revisão (tipo_etapa_id = 2)
    rev_atividade_id            integer,
    rev_usuario_id              integer,
    rev_tipo_situacao_id        integer,
    rev_tipo_situacao_nome      text,

    -- Atividade de correção (tipo_etapa_id = 3)
    cor_atividade_id            integer,
    cor_usuario_id              integer,
    cor_tipo_situacao_id        integer,
    cor_tipo_situacao_nome      text,
    cor_observacao              text,

    -- Atividade de revisão+correção (tipo_etapa_id = 4)
    revcor_atividade_id         integer,
    revcor_usuario_id           integer,
    revcor_tipo_situacao_id     integer,
    revcor_tipo_situacao_nome   text,
    revcor_observacao           text,

    -- Atividade de revisão final (tipo_etapa_id = 5)
    revfinal_atividade_id       integer,
    revfinal_usuario_id         integer,
    revfinal_tipo_situacao_id   integer,
    revfinal_tipo_situacao_nome text,

    -- Ambiguidade de etapa por tipo (TRUE = INCONSISTENTE_CICLO)
    exec_ambigua                boolean     NOT NULL DEFAULT FALSE,
    rev_ambigua                 boolean     NOT NULL DEFAULT FALSE,
    cor_ambigua                 boolean     NOT NULL DEFAULT FALSE,
    revcor_ambigua              boolean     NOT NULL DEFAULT FALSE,
    revfinal_ambigua            boolean     NOT NULL DEFAULT FALSE,

    -- Ciclo detectado
    ciclo_modelo                text        NOT NULL,

    -- Totais do histórico de atividades
    total_atividades                        integer,
    total_finalizada_ou_nao_finalizada      integer,
    total_finalizadas                       integer,
    total_nao_finalizadas                   integer,
    total_pendentes                         integer,
    possui_nao_finalizada_no_historico      boolean,
    somente_finalizada_ou_nao_finalizada    boolean,
    observacoes_concatenadas                text,

    -- Datas do fluxo
    -- data_inicio_fluxo : sempre preenchida quando há atividades
    -- data_fim_fluxo    : NULL enquanto concluida = FALSE
    data_inicio_fluxo                       timestamptz,
    data_fim_fluxo                          timestamptz,

    PRIMARY KEY (ut_id)
);
""".strip()

SQL_FLUXO_UT = f"""
WITH
{_CTE_UT_BASE},
{_CTE_ETAPA_CANONICA},
{_CTE_ATIVIDADE_VIGENTE},
{_CTE_PIVOT_VIGENTE},
historico_ut AS (
    SELECT
        atv.unidade_trabalho_id                                             AS ut_id,
        etapa.subfase_id,
        COUNT(*)                                                            AS total_atividades,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id IN (4, 5))             AS total_finalizada_ou_nao_finalizada,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id = 4)                   AS total_finalizadas,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id = 5)                   AS total_nao_finalizadas,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id IN (1, 2, 3))          AS total_pendentes,
        BOOL_OR(atv.tipo_situacao_id = 5)                                  AS possui_nao_finalizada_no_historico,
        BOOL_AND(atv.tipo_situacao_id IN (4, 5))                           AS somente_finalizada_ou_nao_finalizada,
        MIN(atv.data_inicio)                                               AS data_inicio_fluxo,
        MAX(atv.data_fim)                                                  AS data_fim_raw
    FROM {_S}.macrocontrole_atividade atv
    JOIN {_S}.macrocontrole_etapa etapa ON etapa.id  = atv.etapa_id
    GROUP BY atv.unidade_trabalho_id, etapa.subfase_id
),
historico_obs AS (
    SELECT
        atv.unidade_trabalho_id                                             AS ut_id,
        etapa.subfase_id,
        STRING_AGG(
            CASE
                WHEN atv.observacao IS NOT NULL AND BTRIM(atv.observacao) <> ''
                THEN te.nome || ': ' || ts.nome || ' -> ' ||
                     REGEXP_REPLACE(BTRIM(atv.observacao), '\\s+', ' ', 'g')
            END,
            ' | '
            ORDER BY te.nome, atv.id
        )                                                                   AS observacoes_concatenadas
    FROM {_S}.macrocontrole_atividade atv
    JOIN {_S}.macrocontrole_etapa etapa ON etapa.id  = atv.etapa_id
    JOIN {_S}.dominio_tipo_etapa te     ON te.code   = etapa.tipo_etapa_id
    JOIN {_S}.dominio_tipo_situacao ts  ON ts.code   = atv.tipo_situacao_id
    GROUP BY atv.unidade_trabalho_id, etapa.subfase_id
),
-- Detecta se o fluxo está fechado inline (mesma lógica de validacao_fluxo,
-- sem poder fazer JOIN nela pois ainda não foi materializada)
ciclo_pivot AS (
    SELECT
        ub.ut_id,
        ub.subfase_id,
        ub.projeto_id,
        ub.projeto_nome,
        ub.lote_nome,
        ub.bloco_nome,
        ub.fase_nome,
        ub.subfase_nome,
        ub.ut_disponivel,
        ub.ut_dificuldade,
        pv.exec_atividade_id,
        pv.exec_usuario_id,
        pv.exec_tipo_situacao_id,
        pv.exec_tipo_situacao_nome,
        pv.rev_atividade_id,
        pv.rev_usuario_id,
        pv.rev_tipo_situacao_id,
        pv.rev_tipo_situacao_nome,
        pv.cor_atividade_id,
        pv.cor_usuario_id,
        pv.cor_tipo_situacao_id,
        pv.cor_tipo_situacao_nome,
        pv.cor_observacao,
        pv.revcor_atividade_id,
        pv.revcor_usuario_id,
        pv.revcor_tipo_situacao_id,
        pv.revcor_tipo_situacao_nome,
        pv.revcor_observacao,
        pv.revfinal_atividade_id,
        pv.revfinal_usuario_id,
        pv.revfinal_tipo_situacao_id,
        pv.revfinal_tipo_situacao_nome,
        COALESCE(pv.exec_ambigua,     FALSE)  AS exec_ambigua,
        COALESCE(pv.rev_ambigua,      FALSE)  AS rev_ambigua,
        COALESCE(pv.cor_ambigua,      FALSE)  AS cor_ambigua,
        COALESCE(pv.revcor_ambigua,   FALSE)  AS revcor_ambigua,
        COALESCE(pv.revfinal_ambigua, FALSE)  AS revfinal_ambigua,
        -- Ciclo detectado
        CASE
            WHEN COALESCE(pv.exec_ambigua, FALSE)
              OR COALESCE(pv.rev_ambigua, FALSE)
              OR COALESCE(pv.cor_ambigua, FALSE)
              OR COALESCE(pv.revcor_ambigua, FALSE)
              OR COALESCE(pv.revfinal_ambigua, FALSE)
                THEN 'INCONSISTENTE_CICLO'
            WHEN pv.exec_atividade_id     IS NOT NULL
             AND pv.rev_atividade_id      IS NOT NULL
             AND pv.cor_atividade_id      IS NOT NULL
             AND pv.revcor_atividade_id   IS NULL
             AND pv.revfinal_atividade_id IS NULL
                THEN 'CICLO_1_PADRAO'
            WHEN pv.exec_atividade_id     IS NOT NULL
             AND pv.rev_atividade_id      IS NULL
             AND pv.cor_atividade_id      IS NULL
             AND pv.revcor_atividade_id   IS NOT NULL
             AND pv.revfinal_atividade_id IS NULL
                THEN 'CICLO_2_REVISAO_CORRECAO'
            WHEN pv.exec_atividade_id     IS NOT NULL
             AND pv.rev_atividade_id      IS NOT NULL
             AND pv.cor_atividade_id      IS NULL
             AND pv.revcor_atividade_id   IS NULL
             AND pv.revfinal_atividade_id IS NULL
                THEN 'CICLO_3_SEM_CORRECAO'
            WHEN pv.exec_atividade_id     IS NOT NULL
             AND pv.revcor_atividade_id   IS NULL
             AND pv.revfinal_atividade_id IS NOT NULL
                THEN 'CICLO_4_REVISAO_FINAL'
            ELSE 'INCONSISTENTE_CICLO'
        END AS ciclo_modelo
    FROM ut_base ub
    LEFT JOIN pivot_vigente pv
      ON pv.ut_id = ub.ut_id AND pv.subfase_id = ub.subfase_id
)
SELECT
    cp.projeto_id,
    cp.projeto_nome,
    cp.lote_nome,
    cp.bloco_nome,
    cp.fase_nome,
    cp.subfase_id,
    cp.subfase_nome,
    cp.ut_id,
    cp.ut_disponivel,
    cp.ut_dificuldade,

    cp.exec_atividade_id,
    cp.exec_usuario_id,
    cp.exec_tipo_situacao_id,
    cp.exec_tipo_situacao_nome,

    cp.rev_atividade_id,
    cp.rev_usuario_id,
    cp.rev_tipo_situacao_id,
    cp.rev_tipo_situacao_nome,

    cp.cor_atividade_id,
    cp.cor_usuario_id,
    cp.cor_tipo_situacao_id,
    cp.cor_tipo_situacao_nome,
    cp.cor_observacao,

    cp.revcor_atividade_id,
    cp.revcor_usuario_id,
    cp.revcor_tipo_situacao_id,
    cp.revcor_tipo_situacao_nome,
    cp.revcor_observacao,

    cp.revfinal_atividade_id,
    cp.revfinal_usuario_id,
    cp.revfinal_tipo_situacao_id,
    cp.revfinal_tipo_situacao_nome,

    cp.exec_ambigua,
    cp.rev_ambigua,
    cp.cor_ambigua,
    cp.revcor_ambigua,
    cp.revfinal_ambigua,
    cp.ciclo_modelo,

    COALESCE(hs.total_atividades, 0)                                       AS total_atividades,
    COALESCE(hs.total_finalizada_ou_nao_finalizada, 0)                     AS total_finalizada_ou_nao_finalizada,
    COALESCE(hs.total_finalizadas, 0)                                      AS total_finalizadas,
    COALESCE(hs.total_nao_finalizadas, 0)                                  AS total_nao_finalizadas,
    COALESCE(hs.total_pendentes, 0)                                        AS total_pendentes,
    COALESCE(hs.possui_nao_finalizada_no_historico, FALSE)                 AS possui_nao_finalizada_no_historico,
    COALESCE(hs.somente_finalizada_ou_nao_finalizada, FALSE)               AS somente_finalizada_ou_nao_finalizada,
    ho.observacoes_concatenadas,

    hs.data_inicio_fluxo,

    -- data_fim_fluxo: NULL enquanto o fluxo não estiver concluído.
    -- Fluxo fechado inline: todas etapas do ciclo finalizadas (tipo_situacao_id=4)
    -- E somente_finalizada_ou_nao_finalizada = TRUE.
    -- NULL BETWEEN 1 AND 9 = NULL → nunca usado aqui; lógica só usa = 4 com COALESCE.
    CASE
        WHEN cp.ciclo_modelo = 'INCONSISTENTE_CICLO'                       THEN NULL
        WHEN COALESCE(cp.exec_tipo_situacao_id, 0) <> 4                    THEN NULL
        WHEN cp.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_3_SEM_CORRECAO')
         AND COALESCE(cp.rev_tipo_situacao_id, 0) <> 4                     THEN NULL
        WHEN cp.ciclo_modelo = 'CICLO_1_PADRAO'
         AND COALESCE(cp.cor_tipo_situacao_id, 0) <> 4                     THEN NULL
        WHEN cp.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
         AND COALESCE(cp.revcor_tipo_situacao_id, 0) <> 4                  THEN NULL
        WHEN cp.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'
         AND COALESCE(cp.revfinal_tipo_situacao_id, 0) <> 4                THEN NULL
        WHEN NOT COALESCE(hs.somente_finalizada_ou_nao_finalizada, FALSE)  THEN NULL
        ELSE hs.data_fim_raw
    END                                                                    AS data_fim_fluxo

FROM ciclo_pivot cp
LEFT JOIN historico_ut hs
  ON hs.ut_id = cp.ut_id AND hs.subfase_id = cp.subfase_id
LEFT JOIN historico_obs ho
  ON ho.ut_id = cp.ut_id AND ho.subfase_id = cp.subfase_id
""".strip()


# ===========================================================================
# Tabela 2 — kpi.participantes_ut
# ===========================================================================

DDL_PARTICIPANTES_UT = f"""
CREATE TABLE IF NOT EXISTS {_K}.participantes_ut (
    ut_id               integer     NOT NULL,
    papel               text        NOT NULL,
    atividade_id        integer,
    usuario_id          integer,
    usuario_nome        text,
    tipo_situacao_id    integer,
    tipo_situacao_nome  text,
    eh_revisao_vigente  boolean     NOT NULL DEFAULT FALSE,

    PRIMARY KEY (ut_id, papel)
);
""".strip()

SQL_PARTICIPANTES_UT = f"""
WITH flu AS (SELECT * FROM {_K}.fluxo_ut),
usr AS (
    SELECT id AS usuario_id, nome AS usuario_nome
    FROM {_S}.dgeo_usuario
),
papeis AS (
    SELECT
        f.ut_id,
        'EXECUTOR'                                             AS papel,
        f.exec_atividade_id                                    AS atividade_id,
        f.exec_usuario_id                                      AS usuario_id,
        f.exec_tipo_situacao_id                                AS tipo_situacao_id,
        f.exec_tipo_situacao_nome                              AS tipo_situacao_nome,
        FALSE                                                  AS eh_revisao_vigente
    FROM flu f
    WHERE f.exec_atividade_id IS NOT NULL

    UNION ALL

    SELECT
        f.ut_id,
        'REVISOR'                                              AS papel,
        f.rev_atividade_id,
        f.rev_usuario_id,
        f.rev_tipo_situacao_id,
        f.rev_tipo_situacao_nome,
        f.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_3_SEM_CORRECAO') AS eh_revisao_vigente
    FROM flu f
    WHERE f.rev_atividade_id IS NOT NULL

    UNION ALL

    SELECT
        f.ut_id,
        'CORRETOR'                                             AS papel,
        f.cor_atividade_id,
        f.cor_usuario_id,
        f.cor_tipo_situacao_id,
        f.cor_tipo_situacao_nome,
        FALSE                                                  AS eh_revisao_vigente
    FROM flu f
    WHERE f.cor_atividade_id IS NOT NULL

    UNION ALL

    SELECT
        f.ut_id,
        'REVISOR_CORRECAO'                                     AS papel,
        f.revcor_atividade_id,
        f.revcor_usuario_id,
        f.revcor_tipo_situacao_id,
        f.revcor_tipo_situacao_nome,
        f.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'           AS eh_revisao_vigente
    FROM flu f
    WHERE f.revcor_atividade_id IS NOT NULL

    UNION ALL

    SELECT
        f.ut_id,
        'REVISOR_FINAL'                                        AS papel,
        f.revfinal_atividade_id,
        f.revfinal_usuario_id,
        f.revfinal_tipo_situacao_id,
        f.revfinal_tipo_situacao_nome,
        f.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'              AS eh_revisao_vigente
    FROM flu f
    WHERE f.revfinal_atividade_id IS NOT NULL
)
SELECT
    p.ut_id,
    p.papel,
    p.atividade_id,
    p.usuario_id,
    u.usuario_nome,
    p.tipo_situacao_id,
    p.tipo_situacao_nome,
    p.eh_revisao_vigente
FROM papeis p
LEFT JOIN usr u ON u.usuario_id = p.usuario_id
""".strip()


# ===========================================================================
# Tabela 3 — kpi.validacao_fluxo
# ===========================================================================

DDL_VALIDACAO_FLUXO = f"""
CREATE TABLE IF NOT EXISTS {_K}.validacao_fluxo (
    ut_id                       integer     NOT NULL,
    ciclo_modelo                text        NOT NULL,
    exec_finalizada             boolean,
    revisao_vigente_finalizada  boolean,
    cor_finalizada              boolean,
    fluxo_fechado               boolean     NOT NULL,
    etapa_bloqueante            text,

    PRIMARY KEY (ut_id)
);
""".strip()

SQL_VALIDACAO_FLUXO = f"""
SELECT
    f.ut_id,
    f.ciclo_modelo,

    (f.exec_tipo_situacao_id = 4)                              AS exec_finalizada,

    CASE
        WHEN f.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_3_SEM_CORRECAO')
            THEN (f.rev_tipo_situacao_id = 4)
        WHEN f.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
            THEN (f.revcor_tipo_situacao_id = 4)
        WHEN f.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'
            THEN (f.revfinal_tipo_situacao_id = 4)
        ELSE NULL
    END                                                        AS revisao_vigente_finalizada,

    CASE
        WHEN f.ciclo_modelo = 'CICLO_1_PADRAO'
            THEN (f.cor_tipo_situacao_id = 4)
        ELSE NULL
    END                                                        AS cor_finalizada,

    CASE
        WHEN f.ciclo_modelo = 'INCONSISTENTE_CICLO'           THEN FALSE
        WHEN COALESCE(f.exec_tipo_situacao_id, 0) <> 4        THEN FALSE
        WHEN f.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_3_SEM_CORRECAO')
         AND COALESCE(f.rev_tipo_situacao_id, 0) <> 4         THEN FALSE
        WHEN f.ciclo_modelo = 'CICLO_1_PADRAO'
         AND COALESCE(f.cor_tipo_situacao_id, 0) <> 4         THEN FALSE
        WHEN f.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
         AND COALESCE(f.revcor_tipo_situacao_id, 0) <> 4      THEN FALSE
        WHEN f.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'
         AND COALESCE(f.revfinal_tipo_situacao_id, 0) <> 4    THEN FALSE
        WHEN NOT f.somente_finalizada_ou_nao_finalizada        THEN FALSE
        ELSE TRUE
    END                                                        AS fluxo_fechado,

    CASE
        WHEN f.ciclo_modelo = 'INCONSISTENTE_CICLO'           THEN 'CICLO_INVALIDO'
        WHEN COALESCE(f.exec_tipo_situacao_id, 0) <> 4        THEN 'EXECUTOR'
        WHEN f.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_3_SEM_CORRECAO')
         AND COALESCE(f.rev_tipo_situacao_id, 0) <> 4         THEN 'REVISAO'
        WHEN f.ciclo_modelo = 'CICLO_1_PADRAO'
         AND COALESCE(f.cor_tipo_situacao_id, 0) <> 4         THEN 'CORRECAO'
        WHEN f.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
         AND COALESCE(f.revcor_tipo_situacao_id, 0) <> 4      THEN 'REVISAO'
        WHEN f.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'
         AND COALESCE(f.revfinal_tipo_situacao_id, 0) <> 4    THEN 'REVISAO'
        ELSE NULL
    END                                                        AS etapa_bloqueante

FROM {_K}.fluxo_ut f
""".strip()


# ===========================================================================
# Tabela 4 — kpi.validacao_nota
#
# ocorrencia classifica o resultado da validação para todos os ciclos:
#   NOTA_VALIDA          — nota entre 1 e 9, ciclos 1 e 2
#   NOTA_AUSENTE         — nota não encontrada na observação, ciclos 1 e 2
#   NOTA_INVALIDA        — nota fora do intervalo 1-9, ciclos 1 e 2
#   DISTRIBUICAO_DEFAULT — ciclos 3 e 4 (sem nota, distribuição fixa 40/60)
#   CICLO_INVALIDO       — ciclo INCONSISTENTE_CICLO
#
# ATENÇÃO: NULL BETWEEN 1 AND 9 = NULL em SQL (não FALSE).
# Sempre usar COALESCE(expr BETWEEN 1 AND 9, FALSE) em contexto booleano.
# ===========================================================================

DDL_VALIDACAO_NOTA = f"""
CREATE TABLE IF NOT EXISTS {_K}.validacao_nota (
    ut_id               integer     NOT NULL,
    ciclo_modelo        text        NOT NULL,
    nota_qualidade      integer,
    texto_qualidade     text,
    nota_valida         boolean     NOT NULL,
    ocorrencia          text        NOT NULL,

    PRIMARY KEY (ut_id)
);
""".strip()

SQL_VALIDACAO_NOTA = f"""
WITH flu AS (SELECT * FROM {_K}.fluxo_ut),
nota_correcao AS (
    SELECT
        f.ut_id,
        p.nota   AS nota_correcao,
        p.texto  AS texto_nota_correcao
    FROM flu f
    LEFT JOIN LATERAL (
        SELECT (m)[1]::integer AS nota, BTRIM((m)[2]) AS texto
        FROM (
            SELECT
                REGEXP_MATCHES(BTRIM(seg.segmento), '^([1-9])\\s*;\\s*(.+)$') AS m,
                seg.ord
            FROM UNNEST(STRING_TO_ARRAY(COALESCE(f.cor_observacao, ''), '|'))
                 WITH ORDINALITY AS seg(segmento, ord)
        ) x
        WHERE x.m IS NOT NULL
        ORDER BY x.ord LIMIT 1
    ) p ON TRUE
),
nota_revcor AS (
    SELECT
        f.ut_id,
        p.nota   AS nota_revcor,
        p.texto  AS texto_nota_revcor
    FROM flu f
    LEFT JOIN LATERAL (
        SELECT (m)[1]::integer AS nota, BTRIM((m)[2]) AS texto
        FROM (
            SELECT
                REGEXP_MATCHES(BTRIM(seg.segmento), '^([1-9])\\s*;\\s*(.+)$') AS m,
                seg.ord
            FROM UNNEST(STRING_TO_ARRAY(COALESCE(f.revcor_observacao, ''), '|'))
                 WITH ORDINALITY AS seg(segmento, ord)
        ) x
        WHERE x.m IS NOT NULL
        ORDER BY x.ord LIMIT 1
    ) p ON TRUE
),
base AS (
    SELECT
        f.ut_id,
        f.ciclo_modelo,
        CASE
            WHEN f.ciclo_modelo = 'CICLO_1_PADRAO'           THEN nc.nota_correcao
            WHEN f.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN nr.nota_revcor
            ELSE NULL
        END AS nota_qualidade,
        CASE
            WHEN f.ciclo_modelo = 'CICLO_1_PADRAO'           THEN nc.texto_nota_correcao
            WHEN f.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN nr.texto_nota_revcor
            ELSE NULL
        END AS texto_qualidade,
        nc.nota_correcao,
        nr.nota_revcor
    FROM flu f
    LEFT JOIN nota_correcao nc ON nc.ut_id = f.ut_id
    LEFT JOIN nota_revcor   nr ON nr.ut_id = f.ut_id
)
SELECT
    b.ut_id,
    b.ciclo_modelo,
    b.nota_qualidade,
    b.texto_qualidade,

    -- nota_valida: NOT NULL obrigatório.
    -- COALESCE necessário pois NULL BETWEEN 1 AND 9 = NULL em SQL (não FALSE).
    CASE
        WHEN b.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL', 'INCONSISTENTE_CICLO')
            THEN TRUE
        WHEN b.ciclo_modelo = 'CICLO_1_PADRAO'
            THEN COALESCE(b.nota_correcao BETWEEN 1 AND 9, FALSE)
        WHEN b.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
            THEN COALESCE(b.nota_revcor BETWEEN 1 AND 9, FALSE)
        ELSE TRUE
    END                                                        AS nota_valida,

    -- ocorrencia: NOT NULL, classifica o resultado para todos os ciclos.
    CASE
        WHEN b.ciclo_modelo = 'INCONSISTENTE_CICLO'
            THEN 'CICLO_INVALIDO'
        WHEN b.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
            THEN 'DISTRIBUICAO_DEFAULT'
        WHEN b.ciclo_modelo = 'CICLO_1_PADRAO'
            THEN CASE
                WHEN b.nota_correcao IS NULL                            THEN 'NOTA_AUSENTE'
                WHEN b.nota_correcao NOT BETWEEN 1 AND 9                THEN 'NOTA_INVALIDA'
                ELSE 'NOTA_VALIDA'
            END
        WHEN b.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
            THEN CASE
                WHEN b.nota_revcor IS NULL                              THEN 'NOTA_AUSENTE'
                WHEN b.nota_revcor NOT BETWEEN 1 AND 9                  THEN 'NOTA_INVALIDA'
                ELSE 'NOTA_VALIDA'
            END
        ELSE 'NOTA_VALIDA'
    END                                                        AS ocorrencia

FROM base b
""".strip()


# ===========================================================================
# Tabela 5 — kpi.pontos_usuario
#
# Inclui projeto_id, subfase_id e usuario_nome para joins diretos.
# Só tem linhas para UTs com fluxo fechado e nota válida.
# ===========================================================================

DDL_PONTOS_USUARIO = f"""
CREATE TABLE IF NOT EXISTS {_K}.pontos_usuario (
    projeto_id              integer,
    subfase_id              integer,
    ut_id                   integer     NOT NULL,
    usuario_id              integer     NOT NULL,
    usuario_nome            text,
    papel                   text        NOT NULL,
    pontos                  numeric(10, 4)  NOT NULL,
    percentual_dos_pontos   numeric(10, 6),

    PRIMARY KEY (ut_id, papel)
);
""".strip()

SQL_PONTOS_USUARIO = f"""
WITH
flu AS (SELECT * FROM {_K}.fluxo_ut),
vn  AS (SELECT * FROM {_K}.validacao_nota),
vf  AS (SELECT * FROM {_K}.validacao_fluxo),
usr AS (SELECT id AS usuario_id, nome AS usuario_nome FROM {_S}.dgeo_usuario),
concluidas AS (
    SELECT f.*
    FROM flu f
    JOIN vf ON vf.ut_id = f.ut_id AND vf.fluxo_fechado = TRUE
    JOIN vn ON vn.ut_id = f.ut_id AND vn.nota_valida    = TRUE
    WHERE f.ciclo_modelo <> 'INCONSISTENTE_CICLO'
      AND COALESCE(f.ut_dificuldade, 0) > 0
),
percentuais AS (
    SELECT
        c.ut_id,
        c.projeto_id,
        c.subfase_id,
        c.ciclo_modelo,
        c.ut_dificuldade,
        c.exec_usuario_id,
        c.cor_usuario_id,
        c.rev_usuario_id,
        c.revcor_usuario_id,
        c.revfinal_usuario_id,
        vn.nota_qualidade,
        CASE
            WHEN c.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
                THEN 0.40
            -- nota_qualidade não é NULL aqui: nota_valida=TRUE + ciclo com nota
            -- garante nota entre 1 e 9. Sem risco de NULL no cálculo.
            ELSE ROUND((0.4875 - (0.0375 * vn.nota_qualidade))::numeric, 6)
        END                                                    AS perc_revisor,
        CASE
            WHEN c.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
                THEN 0.60
            ELSE ROUND((1.0 - (0.4875 - (0.0375 * vn.nota_qualidade)))::numeric, 6)
        END                                                    AS perc_executor,
        (c.exec_usuario_id IS NOT NULL
         AND c.cor_usuario_id IS NOT NULL
         AND c.exec_usuario_id = c.cor_usuario_id)            AS executor_eh_corretor
    FROM concluidas c
    JOIN vn ON vn.ut_id = c.ut_id
)
-- EXECUTOR
SELECT
    p.projeto_id,
    p.subfase_id,
    p.ut_id,
    p.exec_usuario_id                                          AS usuario_id,
    u.usuario_nome,
    'EXECUTOR'                                                 AS papel,
    CASE
        WHEN p.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
            THEN ROUND((p.ut_dificuldade * 0.60)::numeric, 4)
        WHEN p.executor_eh_corretor
            THEN ROUND((p.ut_dificuldade * p.perc_executor)::numeric, 4)
        ELSE ROUND((p.ut_dificuldade * p.perc_executor * (p.nota_qualidade::numeric / 9.0))::numeric, 4)
    END                                                        AS pontos,
    p.perc_executor                                            AS percentual_dos_pontos
FROM percentuais p
LEFT JOIN usr u ON u.usuario_id = p.exec_usuario_id
WHERE p.exec_usuario_id IS NOT NULL

UNION ALL

-- REVISOR
SELECT
    p.projeto_id,
    p.subfase_id,
    p.ut_id,
    CASE
        WHEN p.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN p.revcor_usuario_id
        WHEN p.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'    THEN p.revfinal_usuario_id
        ELSE p.rev_usuario_id
    END                                                        AS usuario_id,
    u.usuario_nome,
    'REVISOR'                                                  AS papel,
    CASE
        WHEN p.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
            THEN ROUND((p.ut_dificuldade * 0.40)::numeric, 4)
        ELSE ROUND((p.ut_dificuldade * p.perc_revisor)::numeric, 4)
    END                                                        AS pontos,
    p.perc_revisor                                             AS percentual_dos_pontos
FROM percentuais p
LEFT JOIN usr u ON u.usuario_id = CASE
    WHEN p.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN p.revcor_usuario_id
    WHEN p.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'    THEN p.revfinal_usuario_id
    ELSE p.rev_usuario_id
END
WHERE CASE
    WHEN p.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN p.revcor_usuario_id
    WHEN p.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'    THEN p.revfinal_usuario_id
    ELSE p.rev_usuario_id
END IS NOT NULL

UNION ALL

-- CORRETOR (somente CICLO_1_PADRAO)
SELECT
    p.projeto_id,
    p.subfase_id,
    p.ut_id,
    p.cor_usuario_id                                           AS usuario_id,
    u.usuario_nome,
    'CORRETOR'                                                 AS papel,
    CASE
        WHEN p.executor_eh_corretor THEN 0.0000::numeric
        ELSE ROUND((p.ut_dificuldade * p.perc_executor * (1.0 - p.nota_qualidade::numeric / 9.0))::numeric, 4)
    END                                                        AS pontos,
    CASE
        WHEN p.executor_eh_corretor THEN 0.000000::numeric
        ELSE ROUND((p.perc_executor * (1.0 - p.nota_qualidade::numeric / 9.0))::numeric, 6)
    END                                                        AS percentual_dos_pontos
FROM percentuais p
LEFT JOIN usr u ON u.usuario_id = p.cor_usuario_id
WHERE p.ciclo_modelo = 'CICLO_1_PADRAO'
  AND p.cor_usuario_id IS NOT NULL
""".strip()


# ===========================================================================
# Tabela 6 — kpi.estado_ut
#
# data_fim_fluxo vem de fluxo_ut onde já foi calculada como NULL
# quando concluida=FALSE — consistência garantida na fonte.
# ===========================================================================

DDL_ESTADO_UT = f"""
CREATE TABLE IF NOT EXISTS {_K}.estado_ut (
    ut_id                           integer     NOT NULL,
    ciclo_modelo                    text        NOT NULL,
    estado_ut_subfase               text        NOT NULL,
    concluida                       boolean     NOT NULL,

    projeto_nome                    text,
    lote_nome                       text,
    bloco_nome                      text,
    fase_nome                       text,
    subfase_nome                    text,
    ut_disponivel                   boolean,
    ut_dificuldade                  numeric,

    nota_qualidade                  integer,
    texto_qualidade                 text,
    ocorrencia                      text        NOT NULL,
    percentual_producao_revisor     numeric(10, 6),
    percentual_producao_executor    numeric(10, 6),

    usuario_executor_nome           text,
    usuario_executor_exibicao       text,
    executor_tipo_situacao_id       integer,
    executor_tipo_situacao_nome     text,
    usuario_revisor_nome            text,
    revisao_vigente_tipo_situacao_id    integer,
    revisao_vigente_tipo_situacao_nome  text,
    usuario_corretor_nome           text,
    corretor_tipo_situacao_nome     text,

    total_atividades                integer,
    total_finalizadas               integer,
    total_nao_finalizadas           integer,
    total_pendentes                 integer,
    possui_nao_finalizada_no_historico  boolean,
    observacoes_concatenadas        text,
    data_inicio_fluxo               timestamptz,
    data_fim_fluxo                  timestamptz,

    PRIMARY KEY (ut_id)
);
""".strip()

SQL_ESTADO_UT = f"""
WITH
flu AS (SELECT * FROM {_K}.fluxo_ut),
vf  AS (SELECT * FROM {_K}.validacao_fluxo),
vn  AS (SELECT * FROM {_K}.validacao_nota),
pu  AS (SELECT * FROM {_K}.participantes_ut),
executor AS (
    SELECT ut_id, usuario_nome, tipo_situacao_id, tipo_situacao_nome
    FROM pu WHERE papel = 'EXECUTOR'
),
revisor AS (
    SELECT ut_id, usuario_nome, tipo_situacao_id, tipo_situacao_nome
    FROM pu
    WHERE papel IN ('REVISOR', 'REVISOR_CORRECAO', 'REVISOR_FINAL')
      AND eh_revisao_vigente = TRUE
),
corretor AS (
    SELECT ut_id, usuario_nome, tipo_situacao_nome
    FROM pu WHERE papel = 'CORRETOR'
)
SELECT
    f.ut_id,
    f.ciclo_modelo,

    CASE
        WHEN f.ut_disponivel IS FALSE
            THEN 'UT BLOQUEADA'
        WHEN COALESCE(f.ut_dificuldade, 0) = 0
            THEN 'INCONSISTENTE_DIFICULDADE'
        WHEN f.ciclo_modelo = 'INCONSISTENTE_CICLO'
            THEN 'INCONSISTENTE_CICLO'
        WHEN NOT vf.fluxo_fechado AND vf.etapa_bloqueante = 'EXECUTOR'
            THEN 'PENDENTE_EXECUCAO'
        WHEN NOT vf.fluxo_fechado AND vf.etapa_bloqueante = 'REVISAO'
            THEN 'PENDENTE_REVISAO'
        WHEN NOT vf.fluxo_fechado AND vf.etapa_bloqueante = 'CORRECAO'
            THEN 'PENDENTE_CORRECAO'
        WHEN vf.fluxo_fechado AND NOT vn.nota_valida
            THEN 'INCONSISTENTE_NOTA'
        WHEN vf.fluxo_fechado AND vn.nota_valida
         AND f.possui_nao_finalizada_no_historico
         AND f.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
            THEN 'CONCLUIDA_COM_N_Finalizada'
        WHEN vf.fluxo_fechado AND vn.nota_valida
         AND f.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
            THEN 'CONCLUIDA_SEM_CORRECAO'
        WHEN vf.fluxo_fechado AND vn.nota_valida
         AND f.possui_nao_finalizada_no_historico
         AND f.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_2_REVISAO_CORRECAO')
            THEN 'CONCLUIDA_COM_N_Finalizada'
        WHEN vf.fluxo_fechado AND vn.nota_valida
         AND f.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_2_REVISAO_CORRECAO')
            THEN 'CONCLUIDA_COM_CORRECAO'
        ELSE 'INCONSISTENTE_CICLO'
    END                                                        AS estado_ut_subfase,

    COALESCE(vf.fluxo_fechado AND vn.nota_valida, FALSE)       AS concluida,

    f.projeto_nome,
    f.lote_nome,
    f.bloco_nome,
    f.fase_nome,
    f.subfase_nome,
    f.ut_disponivel,
    f.ut_dificuldade,

    vn.nota_qualidade,
    vn.texto_qualidade,
    vn.ocorrencia,

    CASE
        WHEN f.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
            THEN 0.40
        WHEN vn.nota_qualidade BETWEEN 1 AND 9
            THEN ROUND((0.4875 - (0.0375 * vn.nota_qualidade))::numeric, 6)
        ELSE NULL
    END                                                        AS percentual_producao_revisor,

    CASE
        WHEN f.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
            THEN 0.60
        WHEN vn.nota_qualidade BETWEEN 1 AND 9
            THEN ROUND((1.0 - (0.4875 - (0.0375 * vn.nota_qualidade)))::numeric, 6)
        ELSE NULL
    END                                                        AS percentual_producao_executor,

    ex.usuario_nome                                            AS usuario_executor_nome,
    CASE
        WHEN ex.usuario_nome IS NULL OR ex.tipo_situacao_id = 1 THEN 'Não iniciada'
        ELSE COALESCE(ex.usuario_nome, 'Sem usuário')
    END                                                        AS usuario_executor_exibicao,
    ex.tipo_situacao_id                                        AS executor_tipo_situacao_id,
    ex.tipo_situacao_nome                                      AS executor_tipo_situacao_nome,

    rv.usuario_nome                                            AS usuario_revisor_nome,
    rv.tipo_situacao_id                                        AS revisao_vigente_tipo_situacao_id,
    rv.tipo_situacao_nome                                      AS revisao_vigente_tipo_situacao_nome,

    co.usuario_nome                                            AS usuario_corretor_nome,
    co.tipo_situacao_nome                                      AS corretor_tipo_situacao_nome,

    f.total_atividades,
    f.total_finalizadas,
    f.total_nao_finalizadas,
    f.total_pendentes,
    f.possui_nao_finalizada_no_historico,
    f.observacoes_concatenadas,
    f.data_inicio_fluxo,
    -- data_fim_fluxo já é NULL em fluxo_ut quando concluida=FALSE.
    -- Repetido aqui explicitamente para deixar o contrato claro.
    f.data_fim_fluxo

FROM flu f
JOIN vf ON vf.ut_id = f.ut_id
JOIN vn ON vn.ut_id = f.ut_id
LEFT JOIN executor ex ON ex.ut_id = f.ut_id
LEFT JOIN revisor  rv ON rv.ut_id = f.ut_id
LEFT JOIN corretor co ON co.ut_id = f.ut_id
""".strip()


# ===========================================================================
# Tabela 7 — kpi.distribuicao_pontos
#
# Visão wide desnormalizada: uma linha por UT concluída com os pontos de
# cada papel lado a lado — formato ideal para relatórios e BI.
# Depende de: fluxo_ut, validacao_nota, pontos_usuario.
# ===========================================================================

DDL_DISTRIBUICAO_PONTOS = f"""
CREATE TABLE IF NOT EXISTS {_K}.distribuicao_pontos (
    projeto_nome        text,
    subfase_nome        text,
    ut_id               integer     NOT NULL,
    pontos_ut           numeric,
    ciclo_modelo        text        NOT NULL,
    nota_final          integer,
    texto_nota          text,
    nota_valida         boolean     NOT NULL,

    executor_id         integer,
    nome_executor       text,
    pontos_executor     numeric(10, 4),

    corretor_id         integer,
    nome_corretor       text,
    pontos_corretor     numeric(10, 4),

    revisor_id          integer,
    nome_revisor        text,
    pontos_revisor      numeric(10, 4),

    PRIMARY KEY (ut_id)
);
""".strip()

SQL_DISTRIBUICAO_PONTOS = f"""
WITH
flu AS (SELECT * FROM {_K}.fluxo_ut),
vn  AS (SELECT * FROM {_K}.validacao_nota),
pu  AS (SELECT * FROM {_K}.pontos_usuario),
executor AS (
    SELECT ut_id, usuario_id, usuario_nome, pontos FROM pu WHERE papel = 'EXECUTOR'
),
revisor AS (
    SELECT ut_id, usuario_id, usuario_nome, pontos FROM pu WHERE papel = 'REVISOR'
),
corretor AS (
    SELECT ut_id, usuario_id, usuario_nome, pontos FROM pu WHERE papel = 'CORRETOR'
)
SELECT
    f.projeto_nome,
    f.subfase_nome,
    f.ut_id,
    f.ut_dificuldade                                           AS pontos_ut,
    f.ciclo_modelo,
    vn.nota_qualidade                                          AS nota_final,
    vn.texto_qualidade                                         AS texto_nota,
    vn.nota_valida,

    ex.usuario_id                                              AS executor_id,
    ex.usuario_nome                                            AS nome_executor,
    ex.pontos                                                  AS pontos_executor,

    co.usuario_id                                              AS corretor_id,
    co.usuario_nome                                            AS nome_corretor,
    co.pontos                                                  AS pontos_corretor,

    rv.usuario_id                                              AS revisor_id,
    rv.usuario_nome                                            AS nome_revisor,
    rv.pontos                                                  AS pontos_revisor

FROM flu f
JOIN vn  ON vn.ut_id  = f.ut_id
-- Só UTs com pontos calculados (concluídas)
JOIN executor ex ON ex.ut_id = f.ut_id
LEFT JOIN revisor  rv ON rv.ut_id = f.ut_id
LEFT JOIN corretor co ON co.ut_id = f.ut_id
""".strip()


# ===========================================================================
# Catálogo — ordem estrita de materialização
# ===========================================================================

TABELAS_KPI: tuple[tuple[str, str, str], ...] = (
    ("fluxo_ut", DDL_FLUXO_UT, SQL_FLUXO_UT),
    ("participantes_ut", DDL_PARTICIPANTES_UT, SQL_PARTICIPANTES_UT),
    ("validacao_fluxo", DDL_VALIDACAO_FLUXO, SQL_VALIDACAO_FLUXO),
    ("validacao_nota", DDL_VALIDACAO_NOTA, SQL_VALIDACAO_NOTA),
    ("pontos_usuario", DDL_PONTOS_USUARIO, SQL_PONTOS_USUARIO),
    ("estado_ut", DDL_ESTADO_UT, SQL_ESTADO_UT),
    ("distribuicao_pontos", DDL_DISTRIBUICAO_PONTOS, SQL_DISTRIBUICAO_PONTOS),
)
