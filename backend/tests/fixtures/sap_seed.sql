-- =============================================================================
-- SAP seed — banco sap_test
--
-- Estrutura mínima + dados para a suite de testes de integração.
-- Executado no banco sap_test antes de cada rodada de pytest.
-- O pipeline sincronizar_sap_para_snapshot() lê daqui e escreve em cp_test.
--
-- Cenários:
--   UT 1 — CICLO_1_PADRAO, concluída (exec + rev + cor, nota=7)
--   UT 2 — CICLO_3_SEM_CORRECAO, concluída (exec + rev, sem cor)
--   UT 3 — PENDENTE_EXECUCAO (exec em andamento, tipo_situacao=2)
--   UT 4 — UT BLOQUEADA (disponivel = FALSE)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schemas
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS dominio;
CREATE SCHEMA IF NOT EXISTS dgeo;
CREATE SCHEMA IF NOT EXISTS macrocontrole;

-- ---------------------------------------------------------------------------
-- dominio.*
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dominio.status (
    code  smallint PRIMARY KEY,
    nome  text     NOT NULL
);
CREATE TABLE IF NOT EXISTS dominio.tipo_situacao (
    code  smallint PRIMARY KEY,
    nome  text
);
CREATE TABLE IF NOT EXISTS dominio.tipo_etapa (
    code  smallint PRIMARY KEY,
    nome  text     NOT NULL
);
CREATE TABLE IF NOT EXISTS dominio.tipo_fase (
    code  smallint PRIMARY KEY,
    nome  text     NOT NULL,
    cor   text     NOT NULL
);

INSERT INTO dominio.status (code, nome) VALUES
    (1,'Ativo'),(2,'Encerrado'),(3,'Planejado'),(4,'Arquivado'),(5,'Suspenso')
ON CONFLICT DO NOTHING;

INSERT INTO dominio.tipo_situacao (code, nome) VALUES
    (1,'Não iniciada'),(2,'Em execução'),(3,'Pausada'),
    (4,'Finalizada'),(5,'Não finalizada')
ON CONFLICT DO NOTHING;

INSERT INTO dominio.tipo_etapa (code, nome) VALUES
    (1,'Execução'),(2,'Revisão'),(3,'Correção'),
    (4,'Revisão Correção'),(5,'Revisão Final')
ON CONFLICT DO NOTHING;

INSERT INTO dominio.tipo_fase (code, nome, cor) VALUES
    (1,'Fototriangulação','#4A90D9')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- dgeo.*
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dgeo.usuario (
    id                  integer  PRIMARY KEY,
    login               text     NOT NULL,
    nome                text     NOT NULL,
    nome_guerra         text     NOT NULL,
    tipo_turno_id       smallint,
    tipo_posto_grad_id  smallint NOT NULL DEFAULT 1,
    administrador       boolean  NOT NULL DEFAULT false,
    ativo               boolean  NOT NULL DEFAULT true,
    uuid                text     NOT NULL
);

INSERT INTO dgeo.usuario
    (id, login, nome, nome_guerra, tipo_turno_id, tipo_posto_grad_id, administrador, ativo, uuid)
VALUES
    (1,'exec','Executor Teste','Exec',1,1,false,true,'aaaaaaaa-0001-4000-8000-000000000001'),
    (2,'rev','Revisor Teste','Rev',1,1,false,true,'aaaaaaaa-0002-4000-8000-000000000002'),
    (3,'cor','Corretor Teste','Cor',1,1,false,true,'aaaaaaaa-0003-4000-8000-000000000003'),
    (4,'admin','Administrador','Admin',1,1,true,true,'aaaaaaaa-0004-4000-8000-000000000004')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- macrocontrole.*
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS macrocontrole.linha_producao (
    id         integer PRIMARY KEY,
    nome       text    NOT NULL,
    nome_abrev text    NOT NULL
);
CREATE TABLE IF NOT EXISTS macrocontrole.fase (
    id                integer  PRIMARY KEY,
    tipo_fase_id      smallint NOT NULL,
    linha_producao_id integer  NOT NULL,
    ordem             integer  NOT NULL
);
CREATE TABLE IF NOT EXISTS macrocontrole.subfase (
    id      integer PRIMARY KEY,
    nome    text    NOT NULL,
    fase_id integer NOT NULL,
    ordem   integer NOT NULL
);
CREATE TABLE IF NOT EXISTS macrocontrole.projeto (
    id         integer  PRIMARY KEY,
    nome       text     NOT NULL,
    nome_abrev text     NOT NULL,
    descricao  text,
    status_id  smallint NOT NULL
);
CREATE TABLE IF NOT EXISTS macrocontrole.lote (
    id                 integer  PRIMARY KEY,
    nome               text     NOT NULL,
    nome_abrev         text     NOT NULL,
    denominador_escala integer  NOT NULL,
    linha_producao_id  integer  NOT NULL,
    projeto_id         integer  NOT NULL,
    descricao          text,
    status_id          smallint NOT NULL
);
CREATE TABLE IF NOT EXISTS macrocontrole.bloco (
    id         integer  PRIMARY KEY,
    nome       text     NOT NULL,
    prioridade integer  NOT NULL,
    status_id  smallint NOT NULL,
    lote_id    integer  NOT NULL
);
CREATE TABLE IF NOT EXISTS macrocontrole.etapa (
    id            integer  PRIMARY KEY,
    tipo_etapa_id smallint NOT NULL,
    subfase_id    integer  NOT NULL,
    lote_id       integer  NOT NULL,
    ordem         integer  NOT NULL
);
CREATE TABLE IF NOT EXISTS macrocontrole.unidade_trabalho (
    id                     integer  PRIMARY KEY,
    nome                   text,
    epsg                   text     NOT NULL,
    dado_producao_id       integer  NOT NULL,
    subfase_id             integer  NOT NULL,
    lote_id                integer  NOT NULL,
    bloco_id               integer  NOT NULL,
    disponivel             boolean  NOT NULL DEFAULT false,
    dificuldade            numeric  NOT NULL DEFAULT 0,
    tempo_estimado_minutos integer  NOT NULL DEFAULT 0,
    prioridade             integer  NOT NULL DEFAULT 1,
    observacao             text
);
CREATE TABLE IF NOT EXISTS macrocontrole.atividade (
    id                  integer  PRIMARY KEY,
    etapa_id            integer  NOT NULL,
    unidade_trabalho_id integer  NOT NULL,
    usuario_id          integer,
    tipo_situacao_id    smallint NOT NULL,
    data_inicio         timestamptz,
    data_fim            timestamptz,
    observacao          text
);
CREATE TABLE IF NOT EXISTS macrocontrole.perfil_producao (
    id   integer PRIMARY KEY,
    nome text    NOT NULL
);
CREATE TABLE IF NOT EXISTS macrocontrole.perfil_producao_etapa (
    id                 integer  PRIMARY KEY,
    perfil_producao_id integer  NOT NULL,
    subfase_id         integer  NOT NULL,
    tipo_etapa_id      smallint NOT NULL,
    prioridade         integer  NOT NULL
);
CREATE TABLE IF NOT EXISTS macrocontrole.perfil_producao_operador (
    id                 integer PRIMARY KEY,
    usuario_id         integer NOT NULL,
    perfil_producao_id integer NOT NULL
);

-- ---------------------------------------------------------------------------
-- Hierarquia produtiva
-- ---------------------------------------------------------------------------
INSERT INTO macrocontrole.linha_producao (id, nome, nome_abrev) VALUES
    (1,'LP Mapeamento','LPM')
ON CONFLICT DO NOTHING;

INSERT INTO macrocontrole.fase (id, tipo_fase_id, linha_producao_id, ordem) VALUES
    (1, 1, 1, 1)
ON CONFLICT DO NOTHING;

INSERT INTO macrocontrole.subfase (id, nome, fase_id, ordem) VALUES
    (1, 'Extração da Hidrografia e Altimetria', 1, 1)
ON CONFLICT DO NOTHING;

INSERT INTO macrocontrole.projeto (id, nome, nome_abrev, descricao, status_id) VALUES
    (1, 'Projeto Teste Integração', 'PTI', 'Projeto usado nos testes automatizados', 1)
ON CONFLICT DO NOTHING;

INSERT INTO macrocontrole.lote (id, nome, nome_abrev, denominador_escala, linha_producao_id, projeto_id, descricao, status_id) VALUES
    (1, 'Lote Alpha', 'LA', 25000, 1, 1, 'Lote de testes', 1)
ON CONFLICT DO NOTHING;

INSERT INTO macrocontrole.bloco (id, nome, prioridade, status_id, lote_id) VALUES
    (1, 'Bloco Teste Norte', 1, 1, 1)
ON CONFLICT DO NOTHING;

-- Etapas canônicas: exec(1), rev(2), cor(3) para subfase=1, lote=1
INSERT INTO macrocontrole.etapa (id, tipo_etapa_id, subfase_id, lote_id, ordem) VALUES
    (1, 1, 1, 1, 1),
    (2, 2, 1, 1, 2),
    (3, 3, 1, 1, 3)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Unidades de trabalho
-- ---------------------------------------------------------------------------
INSERT INTO macrocontrole.unidade_trabalho
    (id, nome, epsg, dado_producao_id, subfase_id, lote_id, bloco_id, disponivel, dificuldade, tempo_estimado_minutos, prioridade)
VALUES
    (1, 'UT-001', '4326', 1, 1, 1, 1, true,  10, 120, 1),
    (2, 'UT-002', '4326', 1, 1, 1, 1, true,   5,  60, 2),
    (3, 'UT-003', '4326', 1, 1, 1, 1, true,   8,  90, 3),
    (4, 'UT-004', '4326', 1, 1, 1, 1, false,  6,  80, 4)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Atividades  (data_fim dentro de 180 dias para passar no filtro do sync)
-- ---------------------------------------------------------------------------
INSERT INTO macrocontrole.atividade
    (id, etapa_id, unidade_trabalho_id, usuario_id, tipo_situacao_id, data_inicio, data_fim, observacao)
VALUES
    -- UT 1 — exec Finalizada
    (1, 1, 1, 1, 4,
        CURRENT_TIMESTAMP - INTERVAL '90 days',
        CURRENT_TIMESTAMP - INTERVAL '60 days', NULL),
    -- UT 1 — rev Finalizada
    (2, 2, 1, 2, 4,
        CURRENT_TIMESTAMP - INTERVAL '60 days',
        CURRENT_TIMESTAMP - INTERVAL '40 days', NULL),
    -- UT 1 — cor Finalizada, nota '7; Excelente execução'
    (3, 3, 1, 3, 4,
        CURRENT_TIMESTAMP - INTERVAL '40 days',
        CURRENT_TIMESTAMP - INTERVAL '20 days', '7; Excelente execução'),

    -- UT 2 — exec Finalizada
    (4, 1, 2, 1, 4,
        CURRENT_TIMESTAMP - INTERVAL '80 days',
        CURRENT_TIMESTAMP - INTERVAL '50 days', NULL),
    -- UT 2 — rev Finalizada  (sem cor → CICLO_3)
    (5, 2, 2, 2, 4,
        CURRENT_TIMESTAMP - INTERVAL '50 days',
        CURRENT_TIMESTAMP - INTERVAL '30 days', NULL),

    -- UT 3 — exec Em execução (data_fim NULL → passa filtro)
    (6, 1, 3, 1, 2,
        CURRENT_TIMESTAMP - INTERVAL '5 days',
        NULL, NULL)

    -- UT 4: sem atividades (disponivel=FALSE → BLOQUEADA sem precisar)

ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Perfil de produção (pode ficar vazio; sync aceita 0 linhas)
-- ---------------------------------------------------------------------------
INSERT INTO macrocontrole.perfil_producao (id, nome) VALUES
    (1, 'Perfil Padrão')
ON CONFLICT DO NOTHING;
