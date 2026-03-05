CREATE OR REPLACE VIEW sap_analytics.vw_atividade_enriquecida AS
SELECT
    a.id                 AS atividade_id,
    a.unidade_trabalho_id,
    a.etapa_id,

    e.tipo_etapa_id,
    te.nome              AS tipo_etapa_nome,

    a.tipo_situacao_id,
    ts.nome              AS tipo_situacao_nome,

    a.usuario_id,
    a.data_inicio,
    a.data_fim,
    a.observacao,

    (a.tipo_situacao_id = 4) AS is_finalizada
FROM sap_snapshot.macrocontrole_atividade a
JOIN sap_snapshot.macrocontrole_etapa e
    ON e.id = a.etapa_id
JOIN sap_snapshot.dominio_tipo_etapa te
    ON te.code = e.tipo_etapa_id
JOIN sap_snapshot.dominio_tipo_situacao ts
    ON ts.code = a.tipo_situacao_id;
