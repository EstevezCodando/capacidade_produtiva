CREATE OR REPLACE VIEW sap_analytics.vw_ut_enriquecida AS
SELECT
    p.id   AS projeto_id,
    p.nome AS projeto_nome,

    l.id   AS lote_id,
    l.nome AS lote_nome,

    b.id   AS bloco_id,
    b.nome AS bloco_nome,

    sf.id   AS subfase_id,
    sf.nome AS subfase_nome,

    f.id         AS fase_id,
    tf.nome      AS fase_nome,

    ut.id   AS ut_id,
    ut.nome AS ut_nome,

    ut.dificuldade,
    ut.tempo_estimado_minutos
FROM sap_snapshot.macrocontrole_unidade_trabalho ut
JOIN sap_snapshot.macrocontrole_bloco b
    ON b.id = ut.bloco_id
JOIN sap_snapshot.macrocontrole_lote l
    ON l.id = b.lote_id
JOIN sap_snapshot.macrocontrole_projeto p
    ON p.id = l.projeto_id
JOIN sap_snapshot.macrocontrole_subfase sf
    ON sf.id = ut.subfase_id
JOIN sap_snapshot.macrocontrole_fase f
    ON f.id = sf.fase_id
JOIN sap_snapshot.dominio_tipo_fase tf
    ON tf.code = f.tipo_fase_id;
