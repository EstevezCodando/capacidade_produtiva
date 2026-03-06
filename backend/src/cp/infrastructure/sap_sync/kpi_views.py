"""DDL e SQL de materialização da tabela kpi.fato_ut_subfase.

Responsabilidade única: definir o schema da tabela e o SELECT de carga.
A orquestração (TRUNCATE + INSERT) é responsabilidade do kpi_manager.
"""

from __future__ import annotations

_SCHEMA_KPI = "kpi"
_SCHEMA_SNAPSHOT = "sap_snapshot"

# ---------------------------------------------------------------------------
# DDL da tabela — criada pela migration 0004
# ---------------------------------------------------------------------------

DDL_TABELA_FATO_UT_SUBFASE = f"""
CREATE TABLE IF NOT EXISTS {_SCHEMA_KPI}.fato_ut_subfase (
    -- Hierarquia
    projeto_id                              integer         NOT NULL,
    projeto_nome                            text            NOT NULL,
    lote_id                                 integer         NOT NULL,
    lote_nome                               text            NOT NULL,
    bloco_id                                integer         NOT NULL,
    bloco_nome                              text            NOT NULL,
    fase_id                                 integer         NOT NULL,
    fase_nome                               text            NOT NULL,
    subfase_id                              integer         NOT NULL,
    subfase_nome                            text            NOT NULL,
    ut_id                                   integer         NOT NULL,
    ut_nome                                 text            NOT NULL,

    -- Atributos da UT
    ut_disponivel                           boolean,
    ut_dificuldade                          numeric,

    -- Histórico agregado
    total_atividades                        integer,
    total_finalizada_ou_nao_finalizada      integer,
    total_finalizadas                       integer,
    total_nao_finalizadas                   integer,
    total_pendentes                         integer,
    possui_nao_finalizada_no_historico      boolean,
    somente_finalizada_ou_nao_finalizada    boolean,
    observacoes_concatenadas                text,

    -- Execução
    exec_atividade_id                       integer,
    usuario_executor_id                     integer,
    usuario_executor_nome                   text,
    usuario_executor_exibicao               text,
    executor_tipo_situacao_id               integer,
    executor_tipo_situacao_nome             text,

    -- Revisão (vigente — pode ser tipo 2 ou tipo 5 dependendo do ciclo)
    rev_atividade_id                        integer,
    usuario_revisor_id                      integer,
    usuario_revisor_nome                    text,
    usuario_revisor_exibicao                text,
    revisao_vigente_tipo_situacao_id        integer,
    revisao_vigente_tipo_situacao_nome      text,

    -- Correção (somente CICLO_1_PADRAO)
    cor_atividade_id                        integer,
    usuario_corretor_id                     integer,
    usuario_corretor_nome                   text,
    usuario_corretor_exibicao               text,
    corretor_tipo_situacao_id               integer,
    corretor_tipo_situacao_nome             text,

    -- Nota e classificação
    nota_qualidade                          integer,
    texto_qualidade                         text,
    ciclo_modelo                            text            NOT NULL,
    estado_ut_subfase                       text            NOT NULL,
    concluida                               boolean         NOT NULL,

    -- Percentuais calculados
    percentual_producao_revisor             numeric(10, 6),
    percentual_producao_executor            numeric(10, 6),

    -- Pontos calculados
    pontos_executor                         numeric(10, 4),
    pontos_revisor                          numeric(10, 4),
    pontos_corretor                         numeric(10, 4),

    -- Chave primária natural
    PRIMARY KEY (ut_id, subfase_id)
);
""".strip()

# ---------------------------------------------------------------------------
# SELECT de carga — usado no INSERT INTO ... SELECT
#
# Ciclos suportados:
#   CICLO_1_PADRAO            : Exec(4) → Rev(4) → Cor(4)          nota na Cor
#   CICLO_2_REVISAO_CORRECAO  : Exec(4) → RevCor(4)                nota na RevCor
#   CICLO_3_SEM_CORRECAO      : Exec(4) → Rev(4)                   sem nota
#   CICLO_4_REVISAO_FINAL     : Exec(4) → [Rev(4) →] [Cor(4) →] RevFinal(4)
#                               tipo_etapa_id=5, sem nota, 40/60 fixo
#
# Variantes x.1/x.2/x.3 (Não Finalizada intermediária) são capturadas por
# possui_nao_finalizada_no_historico e somente_finalizada_ou_nao_finalizada.
# ---------------------------------------------------------------------------

SQL_SELECT_FATO_UT_SUBFASE = f"""
WITH ut_base AS (
    SELECT
        ut.id                                                  AS ut_id,
        ut.nome                                                AS ut_nome,
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
    FROM {_SCHEMA_SNAPSHOT}.macrocontrole_unidade_trabalho ut
    JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_lote lote
      ON lote.id = ut.lote_id
    JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_bloco bloco
      ON bloco.id = ut.bloco_id
    JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_subfase sf
      ON sf.id = ut.subfase_id
    JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_fase fase
      ON fase.id = sf.fase_id
    JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_fase tf
      ON tf.code = fase.tipo_fase_id
    JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_projeto proj
      ON proj.id = lote.projeto_id
),
etapa_com_min_ordem AS (
    -- Pré-calcula min_ordem por partição para evitar window function dentro de FILTER
    -- (PostgreSQL não permite OVER dentro de FILTER)
    SELECT
        e.id                                                   AS etapa_id,
        e.lote_id,
        e.subfase_id,
        e.tipo_etapa_id,
        e.ordem,
        MIN(e.ordem) OVER (
            PARTITION BY e.lote_id, e.subfase_id, e.tipo_etapa_id
        )                                                      AS min_ordem
    FROM {_SCHEMA_SNAPSHOT}.macrocontrole_etapa e
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
        COUNT(*) FILTER (
            WHERE emo.ordem = emo.min_ordem
        ) OVER (
            PARTITION BY emo.lote_id, emo.subfase_id, emo.tipo_etapa_id
        )                                                      AS qtd_menor_ordem
    FROM etapa_com_min_ordem emo
),
etapa_canonica AS (
    -- Etapa canônica por tipo: menor ordem para o par (lote_id, subfase_id).
    -- Se múltiplas etapas empatam na menor ordem, a UT é marcada ambígua.
    SELECT
        eo.lote_id,
        eo.subfase_id,
        eo.tipo_etapa_id,
        eo.etapa_id,
        (eo.qtd_menor_ordem > 1)                               AS etapa_canonica_ambigua
    FROM etapa_ordenada eo
    WHERE eo.rn = 1
),
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
    FROM {_SCHEMA_SNAPSHOT}.macrocontrole_atividade atv
    JOIN ut_base ub
      ON ub.ut_id = atv.unidade_trabalho_id
    JOIN etapa_canonica ec
      ON ec.etapa_id   = atv.etapa_id
     AND ec.lote_id    = ub.lote_id
     AND ec.subfase_id = ub.subfase_id
    JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_situacao ts
      ON ts.code = atv.tipo_situacao_id
    JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_etapa te
      ON te.code = ec.tipo_etapa_id
),
atividade_vigente AS (
    -- Atividade vigente por (ut_id, subfase_id, tipo_etapa_id): maior id.
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
),
historico_ut_subfase AS (
    SELECT
        atv.unidade_trabalho_id                                AS ut_id,
        etapa.subfase_id,
        COUNT(*)                                               AS total_atividades,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id IN (4, 5)) AS total_finalizada_ou_nao_finalizada,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id = 4)       AS total_finalizadas,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id = 5)       AS total_nao_finalizadas,
        COUNT(*) FILTER (WHERE atv.tipo_situacao_id IN (1, 2, 3)) AS total_pendentes,
        BOOL_OR(atv.tipo_situacao_id = 5)                      AS possui_nao_finalizada_no_historico,
        -- TRUE quando todas as atividades são Finalizada(4) ou Não finalizada(5):
        -- sinal de que não há mais trabalho em andamento nesta UT/subfase.
        BOOL_AND(atv.tipo_situacao_id IN (4, 5))               AS somente_finalizada_ou_nao_finalizada,
        STRING_AGG(
            CASE
                WHEN atv.observacao IS NOT NULL
                 AND BTRIM(atv.observacao) <> ''
                THEN te.nome || ': ' || ts.nome || ' -> ' ||
                     REGEXP_REPLACE(BTRIM(atv.observacao), '\\s+', ' ', 'g')
            END,
            ' | '
            ORDER BY te.nome, atv.id
        )                                                      AS observacoes_concatenadas
    FROM {_SCHEMA_SNAPSHOT}.macrocontrole_atividade atv
    JOIN {_SCHEMA_SNAPSHOT}.macrocontrole_etapa etapa
      ON etapa.id = atv.etapa_id
    JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_etapa te
      ON te.code = etapa.tipo_etapa_id
    JOIN {_SCHEMA_SNAPSHOT}.dominio_tipo_situacao ts
      ON ts.code = atv.tipo_situacao_id
    GROUP BY atv.unidade_trabalho_id, etapa.subfase_id
),
pivot_vigente AS (
    -- Transpõe atividade_vigente: uma linha por (ut_id, subfase_id) com
    -- colunas separadas por tipo_etapa_id (1=Exec, 2=Rev, 3=Cor, 4=RevCor, 5=RevFinal).
    SELECT
        av.ut_id,
        av.subfase_id,

        MAX(CASE WHEN av.tipo_etapa_id = 1 THEN av.atividade_id END)        AS exec_atividade_id,
        MAX(CASE WHEN av.tipo_etapa_id = 1 THEN av.usuario_id END)          AS exec_usuario_id,
        MAX(CASE WHEN av.tipo_etapa_id = 1 THEN av.tipo_situacao_id END)    AS exec_tipo_situacao_id,
        MAX(CASE WHEN av.tipo_etapa_id = 1 THEN av.tipo_situacao_nome END)  AS exec_tipo_situacao_nome,
        MAX(CASE WHEN av.tipo_etapa_id = 1 THEN av.observacao END)          AS exec_observacao,
        BOOL_OR(CASE WHEN av.tipo_etapa_id = 1 THEN av.etapa_canonica_ambigua ELSE FALSE END) AS exec_ambigua,

        MAX(CASE WHEN av.tipo_etapa_id = 2 THEN av.atividade_id END)        AS rev_atividade_id,
        MAX(CASE WHEN av.tipo_etapa_id = 2 THEN av.usuario_id END)          AS rev_usuario_id,
        MAX(CASE WHEN av.tipo_etapa_id = 2 THEN av.tipo_situacao_id END)    AS rev_tipo_situacao_id,
        MAX(CASE WHEN av.tipo_etapa_id = 2 THEN av.tipo_situacao_nome END)  AS rev_tipo_situacao_nome,
        MAX(CASE WHEN av.tipo_etapa_id = 2 THEN av.observacao END)          AS rev_observacao,
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
        MAX(CASE WHEN av.tipo_etapa_id = 5 THEN av.observacao END)          AS revfinal_observacao,
        BOOL_OR(CASE WHEN av.tipo_etapa_id = 5 THEN av.etapa_canonica_ambigua ELSE FALSE END) AS revfinal_ambigua

    FROM atividade_vigente av
    GROUP BY av.ut_id, av.subfase_id
),
nota_correcao AS (
    SELECT
        pv.ut_id,
        pv.subfase_id,
        p.nota                                                  AS nota_correcao,
        p.texto                                                 AS texto_nota_correcao
    FROM pivot_vigente pv
    LEFT JOIN LATERAL (
        SELECT
            (m)[1]::integer                                     AS nota,
            BTRIM((m)[2])                                       AS texto
        FROM (
            SELECT
                REGEXP_MATCHES(BTRIM(seg.segmento), '^([1-9])\\s*;\\s*(.+)$') AS m,
                seg.ord
            FROM UNNEST(STRING_TO_ARRAY(COALESCE(pv.cor_observacao, ''), '|'))
                 WITH ORDINALITY AS seg(segmento, ord)
        ) x
        WHERE x.m IS NOT NULL
        ORDER BY x.ord
        LIMIT 1
    ) p ON TRUE
),
nota_revisao_correcao AS (
    SELECT
        pv.ut_id,
        pv.subfase_id,
        p.nota                                                  AS nota_revisao_correcao,
        p.texto                                                 AS texto_nota_revisao_correcao
    FROM pivot_vigente pv
    LEFT JOIN LATERAL (
        SELECT
            (m)[1]::integer                                     AS nota,
            BTRIM((m)[2])                                       AS texto
        FROM (
            SELECT
                REGEXP_MATCHES(BTRIM(seg.segmento), '^([1-9])\\s*;\\s*(.+)$') AS m,
                seg.ord
            FROM UNNEST(STRING_TO_ARRAY(COALESCE(pv.revcor_observacao, ''), '|'))
                 WITH ORDINALITY AS seg(segmento, ord)
        ) x
        WHERE x.m IS NOT NULL
        ORDER BY x.ord
        LIMIT 1
    ) p ON TRUE
),
usuarios AS (
    SELECT
        u.id                                                    AS usuario_id,
        u.nome                                                  AS usuario_nome
    FROM {_SCHEMA_SNAPSHOT}.dgeo_usuario u
),
consolidado_base AS (
    SELECT
        ub.projeto_id,
        ub.projeto_nome,
        ub.lote_id,
        ub.lote_nome,
        ub.bloco_id,
        ub.bloco_nome,
        ub.fase_id,
        ub.fase_nome,
        ub.subfase_id,
        ub.subfase_nome,
        ub.ut_id,
        ub.ut_nome,
        ub.ut_disponivel,
        ub.ut_dificuldade,

        hs.total_atividades,
        hs.total_finalizada_ou_nao_finalizada,
        hs.total_finalizadas,
        hs.total_nao_finalizadas,
        hs.total_pendentes,
        hs.possui_nao_finalizada_no_historico,
        hs.somente_finalizada_ou_nao_finalizada,
        hs.observacoes_concatenadas,

        pv.exec_atividade_id,
        pv.exec_usuario_id,
        ue.usuario_nome                                         AS usuario_executor_nome,
        pv.exec_tipo_situacao_id,
        pv.exec_tipo_situacao_nome,

        pv.rev_atividade_id,
        pv.rev_usuario_id,
        ur.usuario_nome                                         AS usuario_revisor_nome_revisao,
        pv.rev_tipo_situacao_id,
        pv.rev_tipo_situacao_nome,

        pv.cor_atividade_id,
        pv.cor_usuario_id,
        uc.usuario_nome                                         AS usuario_corretor_nome,
        pv.cor_tipo_situacao_id,
        pv.cor_tipo_situacao_nome,

        pv.revcor_atividade_id,
        pv.revcor_usuario_id,
        urc.usuario_nome                                        AS usuario_revisor_nome_revisao_correcao,
        pv.revcor_tipo_situacao_id,
        pv.revcor_tipo_situacao_nome,

        pv.revfinal_atividade_id,
        pv.revfinal_usuario_id,
        urf.usuario_nome                                        AS usuario_revisor_final_nome,
        pv.revfinal_tipo_situacao_id,
        pv.revfinal_tipo_situacao_nome,

        nc.nota_correcao,
        nc.texto_nota_correcao,
        nrc.nota_revisao_correcao,
        nrc.texto_nota_revisao_correcao,

        CASE
            WHEN COALESCE(pv.exec_ambigua,    FALSE)
              OR COALESCE(pv.rev_ambigua,     FALSE)
              OR COALESCE(pv.cor_ambigua,     FALSE)
              OR COALESCE(pv.revcor_ambigua,  FALSE)
              OR COALESCE(pv.revfinal_ambigua, FALSE)
            THEN 'INCONSISTENTE_CICLO'
            -- Ciclo 1: Exec + Rev + Cor, sem RevCor e sem RevFinal
            WHEN pv.exec_atividade_id     IS NOT NULL
             AND pv.rev_atividade_id      IS NOT NULL
             AND pv.cor_atividade_id      IS NOT NULL
             AND pv.revcor_atividade_id   IS NULL
             AND pv.revfinal_atividade_id IS NULL
            THEN 'CICLO_1_PADRAO'
            -- Ciclo 2: Exec + RevCor, sem Rev e sem Cor e sem RevFinal
            WHEN pv.exec_atividade_id     IS NOT NULL
             AND pv.rev_atividade_id      IS NULL
             AND pv.cor_atividade_id      IS NULL
             AND pv.revcor_atividade_id   IS NOT NULL
             AND pv.revfinal_atividade_id IS NULL
            THEN 'CICLO_2_REVISAO_CORRECAO'
            -- Ciclo 3: Exec + Rev, sem Cor e sem RevCor e sem RevFinal
            WHEN pv.exec_atividade_id     IS NOT NULL
             AND pv.rev_atividade_id      IS NOT NULL
             AND pv.cor_atividade_id      IS NULL
             AND pv.revcor_atividade_id   IS NULL
             AND pv.revfinal_atividade_id IS NULL
            THEN 'CICLO_3_SEM_CORRECAO'
            -- Ciclo 4: Exec + RevFinal (com ou sem Rev e/ou Cor intermediários)
            WHEN pv.exec_atividade_id     IS NOT NULL
             AND pv.revcor_atividade_id   IS NULL
             AND pv.revfinal_atividade_id IS NOT NULL
            THEN 'CICLO_4_REVISAO_FINAL'
            ELSE 'INCONSISTENTE_CICLO'
        END                                                     AS ciclo_modelo
    FROM ut_base ub
    LEFT JOIN historico_ut_subfase hs
      ON hs.ut_id      = ub.ut_id
     AND hs.subfase_id = ub.subfase_id
    LEFT JOIN pivot_vigente pv
      ON pv.ut_id      = ub.ut_id
     AND pv.subfase_id = ub.subfase_id
    LEFT JOIN nota_correcao nc
      ON nc.ut_id      = ub.ut_id
     AND nc.subfase_id = ub.subfase_id
    LEFT JOIN nota_revisao_correcao nrc
      ON nrc.ut_id     = ub.ut_id
     AND nrc.subfase_id = ub.subfase_id
    LEFT JOIN usuarios ue  ON ue.usuario_id  = pv.exec_usuario_id
    LEFT JOIN usuarios ur  ON ur.usuario_id  = pv.rev_usuario_id
    LEFT JOIN usuarios uc  ON uc.usuario_id  = pv.cor_usuario_id
    LEFT JOIN usuarios urc ON urc.usuario_id = pv.revcor_usuario_id
    LEFT JOIN usuarios urf ON urf.usuario_id = pv.revfinal_usuario_id
),
consolidado_regras AS (
    SELECT
        cb.*,

        -- nota_qualidade: nota de 1-9 extraída da observação da etapa revisora
        -- (Correção no ciclo 1, RevCor no ciclo 2; ciclos 3 e 4 não têm nota)
        CASE
            WHEN cb.ciclo_modelo = 'CICLO_1_PADRAO'           THEN cb.nota_correcao
            WHEN cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN cb.nota_revisao_correcao
            ELSE NULL
        END                                                     AS nota_qualidade,

        CASE
            WHEN cb.ciclo_modelo = 'CICLO_1_PADRAO'           THEN cb.texto_nota_correcao
            WHEN cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN cb.texto_nota_revisao_correcao
            ELSE NULL
        END                                                     AS texto_qualidade,

        -- usuario_revisor_id / nome: quem fez a revisão final de cada ciclo
        CASE
            WHEN cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN cb.revcor_usuario_id
            WHEN cb.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'    THEN cb.revfinal_usuario_id
            ELSE cb.rev_usuario_id
        END                                                     AS usuario_revisor_id,

        CASE
            WHEN cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN cb.usuario_revisor_nome_revisao_correcao
            WHEN cb.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'    THEN cb.usuario_revisor_final_nome
            ELSE cb.usuario_revisor_nome_revisao
        END                                                     AS usuario_revisor_nome,

        CASE
            WHEN cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN cb.revcor_tipo_situacao_id
            WHEN cb.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'    THEN cb.revfinal_tipo_situacao_id
            ELSE cb.rev_tipo_situacao_id
        END                                                     AS revisao_vigente_tipo_situacao_id,

        CASE
            WHEN cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO' THEN cb.revcor_tipo_situacao_nome
            WHEN cb.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'    THEN cb.revfinal_tipo_situacao_nome
            ELSE cb.rev_tipo_situacao_nome
        END                                                     AS revisao_vigente_tipo_situacao_nome,

        -- concluida: todas as etapas do ciclo finalizadas (id=4)
        -- + confirmação via somente_finalizada_ou_nao_finalizada (sem trabalho em andamento)
        CASE
            WHEN cb.ciclo_modelo = 'CICLO_1_PADRAO'
             AND cb.exec_tipo_situacao_id = 4
             AND cb.rev_tipo_situacao_id  = 4
             AND cb.cor_tipo_situacao_id  = 4
             AND cb.nota_correcao BETWEEN 1 AND 9
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
            THEN TRUE
            WHEN cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
             AND cb.exec_tipo_situacao_id   = 4
             AND cb.revcor_tipo_situacao_id = 4
             AND cb.nota_revisao_correcao BETWEEN 1 AND 9
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
            THEN TRUE
            WHEN cb.ciclo_modelo = 'CICLO_3_SEM_CORRECAO'
             AND cb.exec_tipo_situacao_id = 4
             AND cb.rev_tipo_situacao_id  = 4
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
            THEN TRUE
            WHEN cb.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'
             AND cb.exec_tipo_situacao_id    = 4
             AND cb.revfinal_tipo_situacao_id = 4
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
            THEN TRUE
            ELSE FALSE
        END                                                     AS concluida,

        CASE
            WHEN cb.ut_disponivel IS FALSE
            THEN 'UT BLOQUEADA'
            WHEN COALESCE(cb.ut_dificuldade, 0) = 0
            THEN 'INCONSISTENTE_DIFICULDADE'
            WHEN cb.ciclo_modelo = 'INCONSISTENTE_CICLO'
            THEN 'INCONSISTENTE_CICLO'
            WHEN COALESCE(cb.exec_tipo_situacao_id, 0) <> 4
            THEN 'PENDENTE_EXECUCAO'
            -- Pendente revisão por ciclo
            WHEN cb.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_3_SEM_CORRECAO')
             AND COALESCE(cb.rev_tipo_situacao_id, 0) <> 4
            THEN 'PENDENTE_REVISAO'
            WHEN cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
             AND COALESCE(cb.revcor_tipo_situacao_id, 0) <> 4
            THEN 'PENDENTE_REVISAO'
            WHEN cb.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'
             AND COALESCE(cb.revfinal_tipo_situacao_id, 0) <> 4
            THEN 'PENDENTE_REVISAO'
            -- Pendente correção (somente ciclo 1)
            WHEN cb.ciclo_modelo = 'CICLO_1_PADRAO'
             AND cb.rev_tipo_situacao_id = 4
             AND COALESCE(cb.cor_tipo_situacao_id, 0) <> 4
            THEN 'PENDENTE_CORRECAO'
            -- Nota inválida (ciclos com nota obrigatória)
            WHEN cb.ciclo_modelo = 'CICLO_1_PADRAO'
             AND cb.cor_tipo_situacao_id = 4
             AND NOT (cb.nota_correcao BETWEEN 1 AND 9)
            THEN 'INCONSISTENTE_NOTA'
            WHEN cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
             AND cb.revcor_tipo_situacao_id = 4
             AND NOT (cb.nota_revisao_correcao BETWEEN 1 AND 9)
            THEN 'INCONSISTENTE_NOTA'
            -- Concluídas com Não Finalizada no histórico
            WHEN cb.ciclo_modelo = 'CICLO_3_SEM_CORRECAO'
             AND cb.exec_tipo_situacao_id = 4
             AND cb.rev_tipo_situacao_id  = 4
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
             AND COALESCE(cb.possui_nao_finalizada_no_historico, FALSE)
            THEN 'CONCLUIDA_COM_N_Finalizada'
            WHEN cb.ciclo_modelo = 'CICLO_3_SEM_CORRECAO'
             AND cb.exec_tipo_situacao_id = 4
             AND cb.rev_tipo_situacao_id  = 4
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
            THEN 'CONCLUIDA_SEM_CORRECAO'
            WHEN cb.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'
             AND cb.exec_tipo_situacao_id    = 4
             AND cb.revfinal_tipo_situacao_id = 4
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
             AND COALESCE(cb.possui_nao_finalizada_no_historico, FALSE)
            THEN 'CONCLUIDA_COM_N_Finalizada'
            WHEN cb.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'
             AND cb.exec_tipo_situacao_id    = 4
             AND cb.revfinal_tipo_situacao_id = 4
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
            THEN 'CONCLUIDA_SEM_CORRECAO'
            WHEN cb.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_2_REVISAO_CORRECAO')
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
             AND (
                    (cb.ciclo_modelo = 'CICLO_1_PADRAO'
                     AND cb.exec_tipo_situacao_id = 4
                     AND cb.rev_tipo_situacao_id  = 4
                     AND cb.cor_tipo_situacao_id  = 4
                     AND cb.nota_correcao BETWEEN 1 AND 9)
                 OR (cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
                     AND cb.exec_tipo_situacao_id   = 4
                     AND cb.revcor_tipo_situacao_id = 4
                     AND cb.nota_revisao_correcao BETWEEN 1 AND 9)
             )
             AND COALESCE(cb.possui_nao_finalizada_no_historico, FALSE)
            THEN 'CONCLUIDA_COM_N_Finalizada'
            WHEN cb.ciclo_modelo IN ('CICLO_1_PADRAO', 'CICLO_2_REVISAO_CORRECAO')
             AND COALESCE(cb.somente_finalizada_ou_nao_finalizada, FALSE)
             AND (
                    (cb.ciclo_modelo = 'CICLO_1_PADRAO'
                     AND cb.exec_tipo_situacao_id = 4
                     AND cb.rev_tipo_situacao_id  = 4
                     AND cb.cor_tipo_situacao_id  = 4
                     AND cb.nota_correcao BETWEEN 1 AND 9)
                 OR (cb.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
                     AND cb.exec_tipo_situacao_id   = 4
                     AND cb.revcor_tipo_situacao_id = 4
                     AND cb.nota_revisao_correcao BETWEEN 1 AND 9)
             )
            THEN 'CONCLUIDA_COM_CORRECAO'
            ELSE 'INCONSISTENTE_CICLO'
        END                                                     AS estado_ut_subfase
    FROM consolidado_base cb
)
SELECT
    cr.projeto_id,
    cr.projeto_nome,
    cr.lote_id,
    cr.lote_nome,
    cr.bloco_id,
    cr.bloco_nome,
    cr.fase_id,
    cr.fase_nome,
    cr.subfase_id,
    cr.subfase_nome,
    cr.ut_id,
    cr.ut_nome,

    cr.ut_disponivel,
    cr.ut_dificuldade,

    cr.total_atividades,
    cr.total_finalizada_ou_nao_finalizada,
    cr.total_finalizadas,
    cr.total_nao_finalizadas,
    cr.total_pendentes,
    cr.possui_nao_finalizada_no_historico,
    cr.somente_finalizada_ou_nao_finalizada,
    cr.observacoes_concatenadas,

    cr.exec_atividade_id,
    cr.exec_usuario_id                                         AS usuario_executor_id,
    cr.usuario_executor_nome,
    CASE
        WHEN cr.exec_atividade_id IS NULL
          OR cr.exec_tipo_situacao_id = 1                      THEN 'Não iniciada'
        ELSE COALESCE(cr.usuario_executor_nome, 'Sem usuário')
    END                                                        AS usuario_executor_exibicao,
    cr.exec_tipo_situacao_id                                   AS executor_tipo_situacao_id,
    cr.exec_tipo_situacao_nome                                 AS executor_tipo_situacao_nome,

    cr.rev_atividade_id,
    cr.usuario_revisor_id,
    cr.usuario_revisor_nome,
    CASE
        WHEN cr.ciclo_modelo = 'CICLO_2_REVISAO_CORRECAO'
         AND (cr.revcor_atividade_id IS NULL OR cr.revisao_vigente_tipo_situacao_id = 1)
        THEN 'Não iniciada'
        WHEN cr.ciclo_modelo = 'CICLO_4_REVISAO_FINAL'
         AND (cr.revfinal_atividade_id IS NULL OR cr.revisao_vigente_tipo_situacao_id = 1)
        THEN 'Não iniciada'
        WHEN cr.ciclo_modelo NOT IN ('CICLO_2_REVISAO_CORRECAO', 'CICLO_4_REVISAO_FINAL')
         AND (cr.rev_atividade_id IS NULL OR cr.revisao_vigente_tipo_situacao_id = 1)
        THEN 'Não iniciada'
        ELSE COALESCE(cr.usuario_revisor_nome, 'Sem usuário')
    END                                                        AS usuario_revisor_exibicao,
    cr.revisao_vigente_tipo_situacao_id,
    cr.revisao_vigente_tipo_situacao_nome,

    cr.cor_atividade_id,
    cr.cor_usuario_id                                          AS usuario_corretor_id,
    cr.usuario_corretor_nome,
    CASE
        WHEN cr.ciclo_modelo <> 'CICLO_1_PADRAO'               THEN NULL
        WHEN cr.cor_atividade_id IS NULL
          OR cr.cor_tipo_situacao_id = 1                       THEN 'Não iniciada'
        ELSE COALESCE(cr.usuario_corretor_nome, 'Sem usuário')
    END                                                        AS usuario_corretor_exibicao,
    cr.cor_tipo_situacao_id                                    AS corretor_tipo_situacao_id,
    cr.cor_tipo_situacao_nome                                  AS corretor_tipo_situacao_nome,

    cr.nota_qualidade,
    cr.texto_qualidade,

    cr.ciclo_modelo,
    cr.estado_ut_subfase,
    cr.concluida,

    -- percentual_producao_revisor: fração da dificuldade que vai para o revisor
    -- Ciclos 3 e 4 (sem nota): 40% fixo
    -- Ciclos 1 e 2 (com nota): fórmula decrescente — nota alta = mais para o executor
    CASE
        WHEN cr.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
        THEN 0.40
        WHEN cr.nota_qualidade BETWEEN 1 AND 9
        THEN ROUND((0.4875 - (0.0375 * cr.nota_qualidade))::numeric, 6)
        ELSE NULL
    END                                                        AS percentual_producao_revisor,

    CASE
        WHEN cr.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
        THEN 0.60
        WHEN cr.nota_qualidade BETWEEN 1 AND 9
        THEN ROUND((1 - (0.4875 - (0.0375 * cr.nota_qualidade)))::numeric, 6)
        ELSE NULL
    END                                                        AS percentual_producao_executor,

    CASE
        WHEN cr.estado_ut_subfase NOT IN (
            'CONCLUIDA_SEM_CORRECAO', 'CONCLUIDA_COM_CORRECAO', 'CONCLUIDA_COM_N_Finalizada'
        ) THEN NULL
        WHEN cr.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
        THEN ROUND((cr.ut_dificuldade * 0.60)::numeric, 4)
        WHEN cr.nota_qualidade BETWEEN 1 AND 9
         AND cr.exec_usuario_id IS NOT NULL
         AND cr.cor_usuario_id  IS NOT NULL
         AND cr.exec_usuario_id = cr.cor_usuario_id
        THEN ROUND((cr.ut_dificuldade * (1 - (0.4875 - (0.0375 * cr.nota_qualidade))))::numeric, 4)
        WHEN cr.nota_qualidade BETWEEN 1 AND 9
        THEN ROUND((cr.ut_dificuldade * (1 - (0.4875 - (0.0375 * cr.nota_qualidade))) * (cr.nota_qualidade::numeric / 9.0))::numeric, 4)
        ELSE NULL
    END                                                        AS pontos_executor,

    CASE
        WHEN cr.estado_ut_subfase NOT IN (
            'CONCLUIDA_SEM_CORRECAO', 'CONCLUIDA_COM_CORRECAO', 'CONCLUIDA_COM_N_Finalizada'
        ) THEN NULL
        WHEN cr.ciclo_modelo IN ('CICLO_3_SEM_CORRECAO', 'CICLO_4_REVISAO_FINAL')
        THEN ROUND((cr.ut_dificuldade * 0.40)::numeric, 4)
        WHEN cr.nota_qualidade BETWEEN 1 AND 9
        THEN ROUND((cr.ut_dificuldade * (0.4875 - (0.0375 * cr.nota_qualidade)))::numeric, 4)
        ELSE NULL
    END                                                        AS pontos_revisor,

    CASE
        WHEN cr.estado_ut_subfase NOT IN (
            'CONCLUIDA_COM_CORRECAO', 'CONCLUIDA_COM_N_Finalizada'
        ) THEN NULL
        WHEN cr.ciclo_modelo <> 'CICLO_1_PADRAO'               THEN NULL
        WHEN cr.nota_qualidade BETWEEN 1 AND 9
         AND cr.exec_usuario_id IS NOT NULL
         AND cr.cor_usuario_id  IS NOT NULL
         AND cr.exec_usuario_id = cr.cor_usuario_id
        THEN 0.0000::numeric
        WHEN cr.nota_qualidade BETWEEN 1 AND 9
        THEN ROUND((cr.ut_dificuldade * (1 - (0.4875 - (0.0375 * cr.nota_qualidade))) * (1 - (cr.nota_qualidade::numeric / 9.0)))::numeric, 4)
        ELSE NULL
    END                                                        AS pontos_corretor

FROM consolidado_regras cr
""".strip()
