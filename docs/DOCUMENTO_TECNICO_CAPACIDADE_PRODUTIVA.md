# Sistema de Gestão Operacional — Capacidade Produtiva
## Documento Técnico de Engenharia de Software

**Versão:** 1.0
**Classificação:** Interno — DSG / Diretoria de Serviço Geográfico
**Domínio:** Gestão de Produção Cartográfica
**Repositório:** `EstevezCodando/capacidade_produtiva`

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Contexto e Dores Resolvidas](#2-contexto-e-dores-resolvidas)
3. [Proposta de Valor e Vantagens](#3-proposta-de-valor-e-vantagens)
4. [Arquitetura do Sistema](#4-arquitetura-do-sistema)
5. [Stack Tecnológica](#5-stack-tecnológica)
6. [Fluxo de Sincronização com o SAP](#6-fluxo-de-sincronização-com-o-sap)
7. [Motor de KPI — Cálculo de Pontos e Desempenho](#7-motor-de-kpi--cálculo-de-pontos-e-desempenho)
8. [Módulo de Agenda e Capacidade](#8-módulo-de-agenda-e-capacidade)
9. [Módulo de Autenticação e Controle de Acesso](#9-módulo-de-autenticação-e-controle-de-acesso)
10. [API REST — Contratos e Endpoints](#10-api-rest--contratos-e-endpoints)
11. [Interface Web — Páginas e Fluxos](#11-interface-web--páginas-e-fluxos)
12. [Modelo de Dados](#12-modelo-de-dados)
13. [Jobs Realizados (JBTs)](#13-jobs-realizados-jbts)
14. [Padrões de Engenharia Aplicados](#14-padrões-de-engenharia-aplicados)
15. [Ciclo de Desenvolvimento e Infraestrutura](#15-ciclo-de-desenvolvimento-e-infraestrutura)
16. [Considerações Finais](#16-considerações-finais)

---

## 1. Visão Geral

O **Capacidade Produtiva** é um sistema de gestão operacional desenvolvido para a **Diretoria de Serviço Geográfico (DSG)** do Exército Brasileiro, com o objetivo de mensurar, controlar e otimizar a produção cartográfica de seus operadores.

O sistema integra-se diretamente ao banco de dados do **SAP institucional** (Sistema de Apoio à Produção) e transforma os dados brutos de atividades em **métricas de desempenho individuais e coletivas**, expressas em pontos, horas e percentuais de conclusão. Ao mesmo tempo, provê uma camada completa de **gestão de agendas** — permitindo ao gestor planejar o que cada operador deverá produzir e registrar o que de fato foi realizado.

O resultado é uma plataforma unificada que une **inteligência operacional** (quem está produzindo o quê, a que velocidade, com qual qualidade) com **controle de capacidade** (quem está disponível, quantas horas cada um tem, quais dias estão consolidados), entregando ao gestor uma visão em tempo quase real da força de trabalho disponível.

---

## 2. Contexto e Dores Resolvidas

### 2.1 O Ambiente de Produção Cartográfica

A DSG organiza sua produção em uma hierarquia rígida:

```
Projeto → Lote → Bloco → Unidade de Trabalho (UT)
```

Cada **Unidade de Trabalho (UT)** percorre um ciclo de produção composto por múltiplas etapas — Execução, Revisão e Correção — cada uma executada por um operador diferente. O progresso de toda a produção é registrado no SAP, que é o sistema-fonte oficial.

### 2.2 Dores Identificadas Antes do Sistema

| # | Dor | Impacto |
|---|-----|---------|
| 1 | **Impossibilidade de medir desempenho individual** — O SAP registra atividades concluídas, mas não consolida pontos por operador/papel/período | Gestores não sabiam quem estava produzindo mais ou menos, nem por quê |
| 2 | **Ausência de controle de horas trabalhadas** — Não havia registro das horas diárias de cada operador | Impossível cruzar horas disponíveis com produção entregue |
| 3 | **Planejamento feito fora do sistema** — Alocações eram feitas em planilhas Excel ou verbalmente | Sem rastreabilidade, sem histórico, sem visibilidade para outros gestores |
| 4 | **Falta de visão de capacidade real** — Férias, licenças, cursos e afastamentos não eram computados sobre a capacidade disponível | Planejamentos inconsistentes com a realidade da equipe |
| 5 | **Dados espalhados e inconsistentes** — KPIs eram calculados manualmente por cada gestor com critérios diferentes | Relatórios conflitantes entre setores |
| 6 | **Nenhuma rastreabilidade de qualidade** — Notas de qualidade das correções (escala 1-9) existiam no SAP mas nunca eram analisadas sistematicamente | Falhas de qualidade repetidas sem visibilidade |
| 7 | **Incapacidade de detectar divergências** — Horas lançadas em blocos que o operador não estava vinculado passavam sem aviso | Dados inconsistentes no SAP sem diagnóstico automático |
| 8 | **Sem histórico temporal** — Sem timeline de produção não era possível comparar a velocidade da equipe ao longo do tempo | Impossível identificar tendências ou sazonalidades |

### 2.3 O que o Sistema Resolve

O Capacidade Produtiva endereça **todas essas dores** com módulos dedicados:

- **Motor de KPI** → resolve as dores 1, 5 e 6
- **Módulo de Agenda** → resolve as dores 2, 3 e 4
- **Sincronização SAP** → resolve a dor 5 (fonte única de verdade)
- **Módulo de Inconsistências** → resolve a dor 7
- **Timeline acumulada** → resolve a dor 8

---

## 3. Proposta de Valor e Vantagens

### 3.1 Para o Gestor / Administrador

| Capacidade | Descrição |
|-----------|-----------|
| **Visão unificada de produção** | Dashboard com progresso por projeto, bloco, subfase e operador em tempo quase real (após sync SAP) |
| **Planejamento com rastreabilidade** | Registro de qual bloco cada operador deve trabalhar, com quantas horas, em qual data — com histórico completo |
| **Controle de capacidade real** | Férias, licenças e cursos são computados e a capacidade líquida disponível é calculada automaticamente |
| **Ranking de produtividade** | Operadores ranqueados por pontos — executor, revisor e corretor — de forma objetiva e auditável |
| **Timeline de evolução** | Gráfico de horas previstas × realizadas × realizadas com extra — por mês ou por dia, para qualquer operador ou bloco |
| **Detecção de divergências** | Relatório de lançamentos em blocos com inconsistências (operador sem vínculo, duplicidade de papéis, etc.) |
| **Consolidação de períodos** | Fechamento formal do período com validação de pendências — impede edições retroativas sem permissão |
| **Exportação de dados** | CSV de operadores sem lançamento, relatórios de capacidade e produção |

### 3.2 Para o Operador

| Capacidade | Descrição |
|-----------|-----------|
| **Dashboard pessoal** | Visão dos próprios blocos, pontos acumulados, horas previstas e realizadas |
| **Minha Agenda** | Calendário interativo com visualização mensal das horas lançadas e previstas |
| **Distribuição de horas** | Gráfico de pizza com a proporção de horas por tipo de atividade em cada mês |
| **Transparência dos pontos** | Cada operador vê exatamente quantos pontos tem — por executor, revisor e corretor — e em qual bloco |

### 3.3 Vantagens Sistêmicas

1. **Fonte única de verdade** — SAP é a única entrada; o sistema nunca altera o SAP, apenas consome seus dados
2. **Auditabilidade total** — Todo lançamento, edição e exclusão gera registro na `audit_log` com estado antes/depois
3. **Idempotência da sincronização** — O sync pode ser executado múltiplas vezes sem duplicar ou corromper dados
4. **Separação de papéis** — O operador só vê os próprios dados; o admin tem visibilidade global
5. **Controle de qualidade integrado** — As notas de qualidade do SAP são extraídas e analisadas junto com os pontos
6. **Escalabilidade de carga** — Dados KPI são materializados em tabelas físicas; as queries de dashboard consultam dados pré-calculados, não o SAP em tempo real

---

## 4. Arquitetura do Sistema

### 4.1 Diagrama de Alto Nível

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENTE WEB (Browser)                       │
│   React 18 + TypeScript + Vite + TanStack Query + CSS Modules       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS / REST JSON
┌───────────────────────────────▼─────────────────────────────────────┐
│                     BACKEND — FastAPI (Python 3.12)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐│
│  │  /auth   │  │  /kpi    │  │ /agenda  │  │  /capacidade /sync   ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │              Camada de Serviços (Domain Services)               ││
│  │  AgendaService  CapacidadeService  ConsolidacaoService          ││
│  │  AuditService   SapSyncService     SyncHistoryService           ││
│  └─────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │              Camada de Repositórios (Data Access)               ││
│  │  CapacidadeDiaRepo  AgendaLancamentoRepo  FeriadoRepo  ...      ││
│  └─────────────────────────────────────────────────────────────────┘│
└──────────┬─────────────────────────────────┬────────────────────────┘
           │ SQLAlchemy 2.0 + psycopg2        │ SQLAlchemy 2.0 + psycopg2
┌──────────▼──────────────┐      ┌────────────▼────────────────────────┐
│   BANCO CP (PostgreSQL) │      │    BANCO SAP (PostgreSQL)           │
│                         │      │                                      │
│  Schema: capacidade     │      │  Schema: dgeo                        │
│  • tipo_atividade       │      │  • usuario                           │
│  • parametro_capacidade │      │  • macrocontrole_*                   │
│  • capacidade_dia       │◄─────│  • dominios_*                        │
│  • agenda_lancamento    │ SYNC │  • atividade (180d window)           │
│  • agenda_prevista_admin│      │                                      │
│  • feriado              │      └──────────────────────────────────────┘
│  • audit_log            │
│                         │
│  Schema: sap_snapshot   │   ← Espelho local do SAP
│  • dgeo_usuario         │
│  • macrocontrole_bloco  │
│  • macrocontrole_ut     │
│  • macrocontrole_fase   │
│  • ...                  │
│                         │
│  Schema: kpi            │   ← Tabelas materializadas de KPI
│  • fluxo_ut             │
│  • pontos_usuario       │
│  • distribuicao_pontos  │
│  • estado_ut            │
│  • ...                  │
└─────────────────────────┘
```

### 4.2 Separação de Responsabilidades

O backend segue arquitetura em camadas inspirada em **Clean Architecture** e **Domain-Driven Design**:

```
src/cp/
├── api/rotas/          ← Camada de Apresentação (HTTP)
│                          Sem lógica de negócio; apenas validação de entrada
│                          e delegação para os serviços
│
├── services/           ← Camada de Aplicação (Lógica de Negócio)
│                          Orquestra repositórios, aplica regras de domínio,
│                          gerencia transações
│
├── repositories/       ← Camada de Persistência (Data Access)
│                          Encapsula toda SQL de leitura/escrita via SQLAlchemy
│
├── domain/             ← Modelos de Domínio
│                          Entidades ORM (SQLAlchemy), Schemas Pydantic,
│                          Enumerações, Constantes de negócio, Exceções
│
├── infrastructure/     ← Infraestrutura Externa
│   ├── sap_sync/          Pipeline de sincronização com o SAP
│   ├── db.py              Criação de engines PostgreSQL
│   └── auth_provider.py   Validação de JWT
│
└── application/        ← Casos de Uso Compostos
                           Orquestração do pipeline SAP completo
```

---

## 5. Stack Tecnológica

### 5.1 Backend

| Componente | Tecnologia | Versão | Justificativa |
|-----------|-----------|--------|---------------|
| Linguagem | Python | 3.12 | Type hints modernos, performance, ecossistema |
| Framework Web | FastAPI | ≥0.115 | Async nativo, OpenAPI automático, Pydantic integrado |
| ORM / SQL | SQLAlchemy | ≥2.0 | ORM maduro, suporte a 2.0 typing, engine pool |
| Driver PostgreSQL | psycopg2-binary | ≥2.9 | Driver C nativo de alta performance |
| Validação | Pydantic Settings | ≥2.0 | Leitura de `config.env` com validação de tipos |
| Migrações | Alembic | ≥1.13 | Controle de versão do schema do banco |
| Servidor ASGI | Uvicorn (standard) | ≥0.32 | Servidor ASGI de produção com workers |
| Autenticação | PyJWT | ≥2.8 | JWT HS256 com claims de expiração |
| Linter/Formatter | Ruff | 0.13 | Lint + format unificados, velocidade C |
| Type Checker | MyPy | 1.18 | Tipagem estática estrita no CI |
| Testes | Pytest + pytest-cov | 8.4 | Suite de testes com cobertura |

### 5.2 Frontend

| Componente | Tecnologia | Versão | Justificativa |
|-----------|-----------|--------|---------------|
| Linguagem | TypeScript | 5.4 | Tipagem estática, IntelliSense, refatoração segura |
| Framework UI | React | 18.3 | Concurrent features, composição de componentes |
| Build Tool | Vite | 5.3 | HMR instantâneo, build otimizado com tree-shaking |
| Data Fetching | TanStack Query | 5.40 | Cache inteligente, staleTime, invalidação automática |
| HTTP Client | Axios | 1.7 | Interceptors para JWT, error handling centralizado |
| Roteamento | React Router DOM | 6.23 | File-based routing, layout aninhado |
| Datas | date-fns | 3.6 | Manipulação de datas sem overhead (tree-shakeable) |
| Estilos | CSS Modules | — | Escopo local por componente, zero runtime |
| Utilitários | clsx | 2.1 | Composição condicional de classes CSS |

### 5.3 Banco de Dados

| Aspecto | Detalhe |
|---------|---------|
| SGBD | PostgreSQL (versão compatível com SAP institucional) |
| Schemas | `capacidade` (dados CP), `sap_snapshot` (espelho SAP), `kpi` (materializações) |
| Migrações | Alembic — 11 versões versionadas, reversíveis |
| Índices | 14 índices nas tabelas KPI materializadas (criados idempotentemente no startup) |
| Conexões | Pool gerenciado pelo SQLAlchemy Engine (separado: engine_cp e engine_sap) |

---

## 6. Fluxo de Sincronização com o SAP

### 6.1 Visão Geral do Pipeline

A sincronização é o coração do sistema. Ela espelha o banco SAP para o schema `sap_snapshot` no banco CP, garantindo que os dados operacionais estejam disponíveis sem latência de rede nas queries de KPI.

```
                      TRIGGER (manual via API ou CLI)
                              │
                              ▼
                    SapSyncService.executar()
                              │
              ┌───────────────┴───────────────┐
              │         sap_sync/sync.py       │
              │                               │
              │  1. Dimensões de Domínio       │
              │     dominio_status             │
              │     dominio_tipo_situacao      │
              │     dominio_tipo_etapa         │
              │     dominio_tipo_fase          │
              │     dominio_situacao_atividade │
              │                               │
              │  2. Usuários                   │
              │     dgeo_usuario               │
              │     (id, login, nome,          │
              │      nome_guerra, ativo, uuid) │
              │                               │
              │  3. Hierarquia de Produção     │
              │     linha_producao             │
              │     fase                       │
              │     subfase                    │
              │     projeto                    │
              │     lote                       │
              │     bloco                      │
              │     etapa                      │
              │     unidade_trabalho           │
              │                               │
              │  4. Fatos (janela 180 dias)    │
              │     atividade (SAP → snapshot) │
              │                               │
              │  5. Perfis de Produção         │
              │     perfil_producao            │
              │     perfil_producao_etapa      │
              │     perfil_producao_operador   │
              │                               │
              │  6. Tipos de Atividade Bloco   │
              │     sync_tipo_atividade_blocos │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │     analytics_manager.py       │
              │  Atualiza views analíticas     │
              │  (sap_analytics.*)             │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │       kpi_manager.py           │
              │  Materializa 7 tabelas KPI    │
              │  (ver seção 7)                │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    sync_history_service.py     │
              │  Registra resultado, duração   │
              │  e status da execução          │
              └───────────────────────────────┘
```

### 6.2 Estratégia de Upsert em Lote

Cada tabela sincronizada usa a estratégia **INSERT ... ON CONFLICT DO UPDATE**:

```sql
INSERT INTO sap_snapshot.{tabela} ({colunas})
VALUES ({valores})
ON CONFLICT ({chave_primaria})
DO UPDATE SET {coluna} = EXCLUDED.{coluna}, ...
```

**Características:**
- **Batch size:** 5.000 linhas por operação (evita lock table e memory pressure)
- **Idempotente:** executar o sync 10 vezes produz o mesmo resultado
- **Eficiente:** atualiza apenas linhas que mudaram (variante `_upsert_quando_mudou`)
- **Atômico:** todo o pipeline em uma única transação — qualquer falha faz rollback completo

### 6.3 Janela Deslizante da Tabela de Fatos

A tabela `macrocontrole_atividade` (fatos de produção) é sincronizada com uma **janela de 180 dias** retroativos. Isso porque:
- O volume completo histórico seria proibitivo (anos de dados)
- Os KPIs operacionais são relevantes nos últimos 6 meses
- As atividades antigas raramente sofrem alteração retroativa

### 6.4 Sincronização de Tipos de Atividade por Bloco

Após sincronizar os blocos, o sistema automaticamente cria entradas em `capacidade.tipo_atividade` para cada bloco ativo:

```python
# Para cada bloco SAP, garante que existe um tipo_atividade com codigo='BLOCO'
# Permite que o operador lance horas associadas a um bloco específico
```

Isso vincula diretamente o **mundo SAP** (blocos cartográficos) ao **mundo Capacidade** (lançamentos de horas).

---

## 7. Motor de KPI — Cálculo de Pontos e Desempenho

### 7.1 Conceito de Pontos

O sistema de pontos é a métrica-chave de desempenho do operador. Cada **Unidade de Trabalho (UT)** possui uma **dificuldade** (peso relativo, tipicamente entre 0 e 1+). Ao concluir uma etapa de uma UT, o operador acumula pontos proporcional à dificuldade da UT e ao seu papel no ciclo.

```
pontos_operador = f(ut_dificuldade, papel, ciclo_produção, conclusão_etapa)
```

### 7.2 Modelos de Ciclo de Produção

O sistema reconhece automaticamente 4 modelos de ciclo, detectados a partir das etapas existentes em cada bloco:

| Ciclo | Etapas | Nota de Qualidade |
|-------|--------|-------------------|
| **CICLO_1_PADRÃO** | Exec(1) → Rev(2) → Cor(3) | Na Correção (etapa 3) |
| **CICLO_2_REVISÃO_CORREÇÃO** | Exec(1) → RevCor(4) | No RevCor (etapa 4) |
| **CICLO_3_SEM_CORREÇÃO** | Exec(1) → Rev(2) | Sem nota |
| **CICLO_4_REVISÃO_FINAL** | Exec(1) → [Rev(2) →] [Cor(3) →] RevFinal(5) | Sem nota |

### 7.3 Pipeline de Materialização KPI (7 Tabelas)

As tabelas KPI são recalculadas a cada sincronização SAP via SQL puro — sem processamento Python de linha por linha, garantindo máxima performance:

```
kpi.fluxo_ut
    ↓
kpi.participantes_ut
    ↓
kpi.validacao_fluxo
    ↓
kpi.validacao_nota
    ↓
kpi.pontos_usuario
    ↓
kpi.estado_ut
    ↓
kpi.distribuicao_pontos  ← Tabela final usada pela API
```

#### **Tabela 1: `kpi.fluxo_ut`** — Detecção do Ciclo + Pivot de Atividades

Para cada UT, detecta qual ciclo está sendo usado e pivota as atividades vigentes (última atividade por papel):

```
ut_id | bloco_id | ciclo | exec_usuario_id | rev_usuario_id | cor_usuario_id | ...
```

A detecção de ciclo usa presença/ausência de etapas:
- Existe etapa 5 (RevFinal) → CICLO_4
- Existe etapa 4 (RevCor) → CICLO_2
- Existe etapa 3 (Correção) → CICLO_1
- Apenas etapas 1+2 → CICLO_3

#### **Tabela 2: `kpi.participantes_ut`** — Unpivot por Papel

Normaliza o fluxo_ut em uma linha por (ut, usuario, papel):
```
ut_id | usuario_id | papel (executor/revisor/corretor)
```

#### **Tabela 3: `kpi.validacao_fluxo`** — Validação de Encerramento

Verifica se o fluxo de cada UT está completo (todas etapas obrigatórias concluídas). Identifica etapas bloqueadoras.

#### **Tabela 4: `kpi.validacao_nota`** — Qualidade

Extrai a nota de qualidade (1-9) do campo `observacao` das atividades de correção. Classifica por faixas:
- 9: excelente
- 7-8: bom
- 5-6: regular
- 1-4: falha

#### **Tabela 5: `kpi.pontos_usuario`** — Cálculo dos Pontos

Calcula os pontos de cada usuário por UT e papel, baseado na dificuldade da UT e no status de conclusão da etapa:

```
ut_id | usuario_id | papel | pontos_calculados
```

#### **Tabela 6: `kpi.estado_ut`** — Estado Consolidado

Agrega tudo numa visão do estado atual de cada UT:
- `concluida` (boolean)
- `data_inicio_fluxo`
- `ut_dificuldade`
- Pontos totais acumulados

#### **Tabela 7: `kpi.distribuicao_pontos`** — Visão Wide para BI/API

Tabela desnormalizada otimizada para leitura:

```
ut_id | bloco_id | subfase_id | executor_id | pontos_executor
                              | revisor_id  | pontos_revisor
                              | corretor_id | pontos_corretor
```

Esta é a tabela consultada pela API do dashboard — uma única scan ao invés de múltiplos JOINs.

### 7.4 Índices de Performance (14 índices)

Criados automaticamente no startup sobre as tabelas KPI:

```sql
-- fluxo_ut
idx_fluxo_ut_bloco_id, idx_fluxo_ut_subfase_id,
idx_fluxo_ut_projeto_id, idx_fluxo_ut_exec_id, idx_fluxo_ut_rev_id

-- distribuicao_pontos
idx_dist_pontos_bloco, idx_dist_pontos_subfase,
idx_dist_pontos_executor, idx_dist_pontos_revisor, idx_dist_pontos_corretor

-- estado_ut
idx_estado_ut_bloco_id, idx_estado_ut_subfase_id

-- pontos_usuario
idx_pontos_usuario_subfase, idx_pontos_usuario_projeto
```

### 7.5 Métricas Disponíveis via API

| Métrica | Endpoint | Descrição |
|---------|----------|-----------|
| Pontos por operador | `/kpi/dashboard` | Ranking de pontos (exec + rev + cor) |
| Progresso por bloco | `/kpi/dashboard` | % de UTs concluídas + pontos realizados/total |
| Horas previstas × realizadas | `/kpi/dashboard` | Timeline acumulada por mês ou por dia |
| Velocidade semanal | `/kpi/dashboard` | UTs concluídas por semana (últimas 8 sem.) |
| Dashboard pessoal | `/kpi/meu-dashboard` | Visão individual — blocos, horas, pontos |
| Distribuição de horas | `/kpi/distribuicao-mensal` | Pizza por tipo de atividade por mês |
| Inconsistências | `/kpi/inconsistencias` | Lançamentos em blocos sem vínculo de operador |

---

## 8. Módulo de Agenda e Capacidade

### 8.1 Conceito de Capacidade

Capacidade é a quantidade de minutos que um operador pode produzir em um dia útil. O sistema distingue:

- **Normal:** dentro do horário padrão (default: 6 horas = 360 min/dia)
- **Extra:** além do horário padrão (default máximo: 4 horas = 240 min/dia)

Os parâmetros são configuráveis por vigência (`parametro_capacidade`), permitindo ajustes quando houver mudanças no expediente.

### 8.2 Materialização Diária de Capacidade

Para cada (operador × dia), o sistema materializa um registro `capacidade_dia` com:

```
capacidade_dia {
  usuario_id
  data
  minutos_capacidade_normal_prevista     ← 0 se férias/feriado/indisp.
  minutos_capacidade_extra_permitida     ← 0 se férias/feriado/indisp.
  eh_dia_util                            ← false se fim de semana
  eh_feriado                             ← true se feriado cadastrado
  eh_indisponivel                        ← true se há indisponibilidade
  status_dia                             ← ABERTO | CONSOLIDADO
}
```

**Hierarquia de prioridade para capacidade zero:**
1. Fim de semana (sábado/domingo) → `eh_dia_util = false`, capacidade = 0
2. Feriado cadastrado → `eh_feriado = true`, capacidade = 0
3. Indisponibilidade do usuário (férias, licença, curso, afastamento) → capacidade = 0
4. Caso contrário: usa `parametro_capacidade.minutos_dia_util_default`

### 8.3 Tipos de Atividade

O sistema categoriza os lançamentos em grupos e códigos:

| Grupo | Código | Descrição |
|-------|--------|-----------|
| PRODUCAO | BLOCO | Horas trabalhadas em bloco cartográfico SAP |
| PRODUCAO | EXTERNA | Produção diversa não vinculada a bloco |
| INDISPONIBILIDADE | FERIAS | Férias regulares |
| INDISPONIBILIDADE | LICENCA | Dispensa médica |
| INDISPONIBILIDADE | CURSO | Capacitação e treinamento |
| INDISPONIBILIDADE | AFASTAMENTO | Dispensa como reconhecimento |
| INDISPONIBILIDADE | CAMPO | Trabalho de campo externo |
| INDISPONIBILIDADE | MILITAR | Atividade militar obrigatória |
| AJUSTE | AJUSTE | Correção administrativa |

### 8.4 Fluxo de Lançamento de Horas (Operador)

```
Operador acessa "Minha Agenda"
        │
        ▼
Seleciona data no calendário mensal
        │
        ▼
Clica em lançar
        │
        ▼
Preenche: tipo_atividade + bloco (se BLOCO) + minutos + faixa (NORMAL/EXTRA)
        │
        ▼
Sistema valida:
  ✓ Data não está consolidada (ou é extra, que é permitida)
  ✓ Data não é futura (operador não pode lançar adiantado)
  ✓ Minutos normais não ultrapassam capacidade normal do dia
  ✓ Minutos extras não ultrapassam máximo de extras
  ✓ Atividade existe e está ativa
        │
        ├── REPROVADO → Retorna erro descritivo
        │
        └── APROVADO → Registra em agenda_lancamento
                              + Registra em audit_log
                              + Invalida cache TanStack Query
```

### 8.5 Fluxo de Planejamento (Admin)

```
Admin acessa "Agenda Prevista"
        │
        ▼
Seleciona operador(es) + data(s) + bloco + minutos
        │
        ▼
Sistema registra em agenda_prevista_admin
        │
        ▼
Operador vê o planejamento no calendário (fundo colorido)
        │
        ▼
Admin compara planejado × realizado no KPI dashboard
```

### 8.6 Consolidação de Períodos

A consolidação é o processo de **fechamento formal** de um período. Após consolidar:

1. **Admin verifica pendências** antes de consolidar:
   - Dias úteis sem nenhum lançamento
   - Lançamentos com total abaixo do esperado
   - Indisponibilidades sem tratamento adequado
   - Inconsistências de calendário

2. **Ao consolidar**, o `status_dia` passa de `ABERTO` → `CONSOLIDADO`

3. **Restrições pós-consolidação:**
   - Operador: não pode editar horas normais (pode editar extra)
   - Admin: acesso irrestrito com registro em audit_log

4. **Desconsolidação:** possível pelo admin, com auditoria automática

### 8.7 Indisponibilidades

O gestor registra períodos de indisponibilidade por tipo:

| Tipo | Impacto |
|------|---------|
| FERIAS | Zera capacidade no período + bloqueia lançamentos |
| LICENCA | Zera capacidade + bloqueia lançamentos |
| CURSO | Zera capacidade + permite lançamento de tipo CURSO |
| AFASTAMENTO | Zera capacidade + bloqueia lançamentos |

---

## 9. Módulo de Autenticação e Controle de Acesso

### 9.1 Fluxo de Autenticação

```
1. Cliente envia POST /api/v1/auth/login
   Body: { usuario: "login_sap", senha: "***" }

2. Backend consulta SAP:
   SELECT id, uuid, administrador
   FROM dgeo.usuario
   WHERE login = :login AND ativo IS TRUE

3. Se encontrado: chama serviço de autenticação SAP
   POST http://10.67.199.48:3010/authenticate
   Body: { usuario, senha, aplicacao: "sap" }

4. Se 201 Success: gera JWT HS256
   Claims: { id, uuid, administrador, exp: agora + 10h }

5. Retorna: { success: true, token: "...", uuid, administrador }

6. Cliente armazena JWT e envia em cada requisição:
   Authorization: Bearer <token>
```

### 9.2 Níveis de Acesso

| Perfil | Acesso | Restrições |
|--------|--------|------------|
| **Operador** | Próprios dados + visão de blocos | Não vê dados de outros usuários |
| **Administrador** | Todos os dados + funções de gestão | Sem restrição funcional |

A distinção é feita pela claim `administrador: true/false` no JWT, validada em cada endpoint via dependency injection do FastAPI.

---

## 10. API REST — Contratos e Endpoints

### 10.1 Base URL

```
http(s)://{host}/api/v1/
```

### 10.2 Endpoints por Módulo

#### Autenticação (`/auth`)
| Método | Path | Autenticação | Descrição |
|--------|------|-------------|-----------|
| POST | `/login` | — | Login com credenciais SAP |

#### Capacidade (`/capacidade`)
| Método | Path | Autenticação | Descrição |
|--------|------|-------------|-----------|
| GET | `/config` | Admin | Configuração de teto diário vigente |
| PUT | `/config` | Admin | Atualizar teto normal e extra |
| POST | `/parametro` | Admin | Criar período de parâmetro |
| GET | `/meu-periodo` | Auth | Resumo de capacidade do operador |
| GET | `/usuario/{id}` | Admin | Capacidade de um usuário específico |
| GET | `/status` | Admin | Status de consolidação por período |
| POST | `/consolidar-periodo` | Admin | Fechar período |
| POST | `/desconsolidar-periodo` | Admin | Reabrir período |
| POST | `/materializar` | Admin | Materializar capacidade_dia |
| GET | `/feriados` | Auth | Listar feriados |
| POST | `/feriados` | Admin | Criar feriado |
| DELETE | `/feriados/{id}` | Admin | Remover feriado |
| GET | `/exportar-sem-lancamento` | Admin | CSV de dias sem lançamento |

#### Agenda (`/agenda`)
| Método | Path | Autenticação | Descrição |
|--------|------|-------------|-----------|
| GET | `/meu-planejamento` | Auth | Planejamento do operador logado |
| GET | `/meus-lancamentos` | Auth | Lançamentos do operador logado |
| POST | `/lancamento` | Auth | Criar lançamento (operador) |
| PUT | `/lancamento/{id}` | Auth | Editar lançamento |
| DELETE | `/lancamento/{id}` | Auth | Remover lançamento |
| POST | `/lancamento/lote` | Auth | Lançamentos em lote |
| GET | `/usuario/{id}` | Admin | Agenda completa de um usuário |
| POST | `/planejamento` | Admin | Planejar para um usuário |
| POST | `/planejamento/lote` | Admin | Planejamento em lote |
| PUT | `/planejamento/{id}` | Admin | Editar planejamento |
| DELETE | `/planejamento/{id}` | Admin | Remover planejamento |
| POST | `/indisponibilidade` | Admin | Criar indisponibilidade |
| DELETE | `/indisponibilidade/{id}` | Admin | Remover indisponibilidade |

#### KPI (`/kpi`)
| Método | Path | Autenticação | Descrição |
|--------|------|-------------|-----------|
| GET | `/dashboard` | Auth | Dashboard global com KPIs + timeline |
| GET | `/meu-dashboard` | Auth | Dashboard pessoal do operador |
| GET | `/projetos` | Auth | Lista de projetos com progresso |
| GET | `/projetos/{id}` | Auth | Detalhes hierárquicos do projeto |
| GET | `/inconsistencias` | Admin | Relatório de inconsistências |
| GET | `/timeline-diario` | Auth | Timeline diária de horas por mês |
| GET | `/distribuicao-mensal` | Admin | Pizza de horas por tipo (admin) |
| GET | `/minha-distribuicao` | Auth | Pizza de horas por tipo (operador) |

#### Sincronização (`/sync`)
| Método | Path | Autenticação | Descrição |
|--------|------|-------------|-----------|
| GET | `/status` | Admin | Status e histórico do último sync |
| POST | `/executar` | Admin | Disparar sincronização manual |

### 10.3 Convenções

- Todas as respostas são JSON
- Erros seguem o padrão FastAPI: `{ "detail": "mensagem" }`
- Paginação: não utilizada (volumes controlados)
- Cache-Control: endpoints KPI retornam `private, max-age=60, stale-while-revalidate=30`
- Autenticação: `Authorization: Bearer <JWT>` em todos os endpoints protegidos

---

## 11. Interface Web — Páginas e Fluxos

### 11.1 Mapa de Páginas

```
/ (redirect)
├── /login                    → Autenticação (pública)
├── /dashboard                → KPI Global + Timeline + Ranking [Admin]
│                               KPI Pessoal + Meus Blocos [Operador]
├── /minha-agenda             → Calendário pessoal + lançamentos [Operador]
├── /agenda-prevista          → Planejamento de operadores [Admin]
├── /agenda-realizada         → Lançamentos de todos operadores [Admin]
├── /blocos                   → Progresso por bloco/projeto
├── /atividades               → Catálogo de atividades
├── /operadores               → Lista e perfil de usuários [Admin]
├── /configuracoes            → Parâmetros, feriados, sync [Admin]
├── /exportar                 → Geração de relatórios CSV
├── /gerenciar-agendas        → Operações em lote [Admin]
└── /perfil                   → Perfil do usuário logado
```

### 11.2 Dashboard (Administrador)

O dashboard administrativo é a página mais rica do sistema. Organizado em seções:

**Seção 1 — Filtros e Contexto**
- Seletor de Bloco (filtra todo o dashboard)
- Seletor de Subfase (filtra ranking)
- Botão de Sincronizar SAP

**Seção 2 — Cards de Métricas**
- Blocos SAP: total de blocos (ou "1 bloco selecionado" quando filtrado)
- Progresso Geral: percentual de pontos realizados × total
- Horas Previstas em Produção
- Horas Lançadas em Produção
- Última Sync SAP: data e status

**Seção 3 — Situação dos Blocos**
- Grid de cards por bloco com:
  - Nome do bloco e projeto (com tooltip de texto completo ao hover)
  - Barra de progresso colorida (verde ≥70%, amarelo ≥35%, vermelho <35%)
  - Contagem de UTs (concluídas / em andamento / não iniciadas / total)
  - Pontos realizados / total
  - Top performers por papel (execução e revisão)

**Seção 4 — Timeline Acumulada**
- Alternância entre visão anual (12 meses) e visão mensal (dia a dia)
- 3 séries: Previsto acumulado · Normal acumulado · Total acumulado
- Tooltip interativo por ponto
- Tooltip de resumo fixo no rodapé

**Seção 5 — Ranking de Produção**
- Tabela de operadores com pontos por papel
- Ordenação por executor / revisor / corretor / total
- Barra de contribuição visual por operador

**Seção 6 — Velocidade Semanal**
- Gráfico de barras com UTs concluídas por semana nas últimas 8 semanas

**Seção 7 — Alertas**
- Dias sem nota de qualidade registrada (pendências de qualidade)

**Seção 8 — Gráfico de Pizza**
- Distribuição de horas por tipo de atividade no mês selecionado
- Fatia "Não alocado" para horas disponíveis não utilizadas
- Hover interativo no centro do donut

### 11.3 Dashboard (Operador)

Versão simplificada e personalizada:
- Meus Blocos: cards com progresso pessoal e pontos
- Contribuição no Bloco: barra de quanto representa do total
- Timeline: horas previstas × realizadas (pessoal, últimos 45 dias)
- Minha Distribuição: pizza de horas por tipo no mês

### 11.4 Calendário (Agenda Prevista / Realizada / Minha Agenda)

- Navegação mensal (mês anterior / hoje / próximo mês)
- Células do calendário com:
  - Indicador de horas lançadas por tipo (barra de cores)
  - Badge de total de minutos
  - Indicação visual de dia indisponível / feriado / fim de semana
  - Indicação de dia consolidado (ícone de cadeado)
- Modal de lançamento com form completo
- Lançamento em lote (múltiplos dias de uma vez)
- Seleção de dias por clique ou arrastar
- DayDetailPanel: painel lateral com detalhes do dia selecionado

---

## 12. Modelo de Dados

### 12.1 Schema `capacidade` (dados proprietários do sistema)

```
┌─────────────────────────────┐
│       tipo_atividade        │
│─────────────────────────────│
│ id         PK               │
│ codigo     VARCHAR (enum)   │ ← CodigoAtividade
│ nome       VARCHAR          │
│ bloco_id   FK → snap.bloco  │ ← nulo se não for BLOCO
│ cor        VARCHAR          │ ← cor hex para UI
│ grupo      VARCHAR (enum)   │ ← GrupoAtividade
└─────────────────────────────┘
            ↑
            │ FK
┌───────────────────────────────────────────┐
│             agenda_lancamento              │
│───────────────────────────────────────────│
│ id                PK                       │
│ usuario_id        FK → snap.dgeo_usuario   │
│ data_lancamento   DATE                     │
│ bloco_id          FK → snap.bloco          │
│ tipo_atividade_id FK → tipo_atividade      │
│ faixa_minuto      VARCHAR (enum)           │ ← NORMAL | EXTRA
│ minutos           INTEGER                  │
│ em_uso            BOOLEAN                  │ ← soft delete
│ consolidado       BOOLEAN                  │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│           agenda_prevista_admin            │
│───────────────────────────────────────────│
│ id                PK                       │
│ usuario_id        FK → snap.dgeo_usuario   │
│ data              DATE                     │
│ bloco_id          FK → snap.bloco          │
│ minutos_planejados_normais    INTEGER      │
│ minutos_planejados_extras     INTEGER      │
│ em_uso            BOOLEAN                  │
│ consolidado       BOOLEAN                  │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│             capacidade_dia                 │
│───────────────────────────────────────────│
│ id                  PK                     │
│ usuario_id          FK → snap.dgeo_usuario │
│ data                DATE                   │
│ minutos_capacidade_normal_prevista  INT    │
│ minutos_capacidade_extra_permitida  INT    │
│ eh_dia_util         BOOLEAN                │
│ eh_feriado          BOOLEAN                │
│ eh_indisponivel     BOOLEAN                │
│ status_dia          VARCHAR (enum)         │ ← ABERTO | CONSOLIDADO
│ UNIQUE (usuario_id, data)                  │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│           parametro_capacidade             │
│───────────────────────────────────────────│
│ id                           PK            │
│ minutos_dia_util_default     INT           │ ← padrão: 360 (6h)
│ minutos_extra_maximo_default INT           │ ← padrão: 240 (4h)
│ data_inicio_vigencia         DATE          │
│ data_fim_vigencia            DATE (NULL)   │ ← NULL = vigente
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│       indisponibilidade_usuario            │
│───────────────────────────────────────────│
│ id              PK                         │
│ usuario_id      FK → snap.dgeo_usuario     │
│ tipo_atividade_id FK → tipo_atividade      │
│ data_inicio     DATE                       │
│ data_fim        DATE                       │
│ descricao       TEXT                       │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│                 feriado                    │
│───────────────────────────────────────────│
│ id          PK                             │
│ data        DATE UNIQUE                    │
│ descricao   TEXT                           │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│               audit_log                    │
│───────────────────────────────────────────│
│ id                PK                       │
│ entidade          VARCHAR                  │ ← nome da tabela
│ entidade_id       INTEGER                  │
│ acao              VARCHAR (enum)           │ ← CREATE|UPDATE|DELETE|...
│ antes_json        JSONB                    │ ← estado anterior
│ depois_json       JSONB                    │ ← estado posterior
│ usuario_executor  INTEGER                  │
│ timestamp         TIMESTAMPTZ              │
└───────────────────────────────────────────┘
```

### 12.2 Schema `kpi` (tabelas materializadas)

| Tabela | Linhas Estimadas | Recriada em |
|--------|-----------------|-------------|
| `fluxo_ut` | 1 por UT ativa | Cada sync |
| `participantes_ut` | 2-3 por UT | Cada sync |
| `validacao_fluxo` | 1 por UT | Cada sync |
| `validacao_nota` | 0-1 por UT (se houver nota) | Cada sync |
| `pontos_usuario` | 1-3 por UT | Cada sync |
| `estado_ut` | 1 por UT | Cada sync |
| `distribuicao_pontos` | 1 por UT | Cada sync |

### 12.3 Schema `sap_snapshot` (espelho SAP, somente leitura pela aplicação)

Contém cópias das tabelas SAP. Principais:

| Tabela | Descrição |
|--------|-----------|
| `dgeo_usuario` | Operadores (com campo `ativo`) |
| `macrocontrole_projeto` | Projetos cartográficos |
| `macrocontrole_lote` | Lotes por projeto |
| `macrocontrole_bloco` | Blocos por lote |
| `macrocontrole_subfase` | Subfases de produção |
| `macrocontrole_unidade_trabalho` | UTs com dificuldade |
| `macrocontrole_atividade` | Fatos de produção (janela 180d) |
| `dominio_tipo_etapa` | Tipos de etapa (Exec, Rev, Cor...) |
| `dominio_tipo_situacao` | Situações de atividade |

---

## 13. Jobs Realizados (JBTs)

Os JBTs (Jobs de Desenvolvimento / Build Tasks) abaixo descrevem as implementações realizadas no sistema desde sua concepção:

### JBT-01 — Estruturação da Arquitetura Base
- Configuração do projeto FastAPI + SQLAlchemy 2.0 + Alembic
- Definição dos schemas `capacidade`, `sap_snapshot`, `kpi`
- Configuração de ambiente com pydantic-settings e `config.env`
- Setup de engines separados para banco CP e banco SAP
- Estruturação das camadas API → Services → Repositories → Domain

### JBT-02 — Pipeline de Sincronização SAP
- Implementação do sync completo de 15 tabelas dimensão + 1 tabela fato
- Estratégia de upsert em lote (5.000 linhas por batch)
- Janela deslizante de 180 dias para atividades
- Atomicidade via transação única (rollback em falha)
- Registro de histórico de execução com duração e status

### JBT-03 — Motor KPI — Materialização em 7 Etapas
- Implementação das 7 tabelas KPI via SQL puro com CTEs
- Detecção automática dos 4 modelos de ciclo de produção
- Pivot de atividades vigentes por papel (exec/rev/cor/revcor/revFinal)
- Cálculo de pontos por (UT, usuário, papel)
- Validação de fluxo completo e extração de notas de qualidade
- Tabela desnormalizada `distribuicao_pontos` para BI/API

### JBT-04 — Autenticação Federada com SAP
- Login federado via `dgeo.usuario` + serviço de autenticação SAP
- Geração de JWT HS256 com claims de perfil
- Middleware de validação de token em todos os endpoints
- Distinção admin/operador via claim JWT

### JBT-05 — Módulo de Capacidade e Agenda
- Modelagem das entidades de domínio (9 tabelas)
- AgendaService com validações de negócio completas
- Materialização de `capacidade_dia` com hierarquia de prioridade
- Gestão de feriados e indisponibilidades
- Faixa NORMAL/EXTRA com limites configuráveis

### JBT-06 — Consolidação de Períodos
- ConsolidacaoService com validação de pendências antes de fechar
- Detecção de 4 tipos de pendência (sem lançamento, incompleto, etc.)
- Restrições pós-consolidação (operador só edita extra)
- Desconsolidação com auditoria

### JBT-07 — Auditoria Completa
- AuditService com log de todos os estados (antes/depois em JSONB)
- Registro automático em CREATE, UPDATE, DELETE, CONSOLIDATE, DECONSOLIDATE

### JBT-08 — Dashboard Administrativo (Frontend)
- Dashboard com filtro de bloco e subfase
- Cards de métricas contextuais (atualizam com filtro)
- Seção "Situação dos Blocos" com cards de progresso
- Ranking de operadores com ordenação multi-coluna
- Timeline acumulada (anual e mensal) com 3 séries
- Gráfico de velocidade semanal
- Alertas de notas ausentes

### JBT-09 — Dashboard do Operador (Frontend)
- Visão personalizada com dados exclusivos do operador logado
- Meus Blocos com contribuição visual
- Timeline pessoal dos últimos 45 dias
- Gráfico de pizza de distribuição de horas por mês

### JBT-10 — Sistema de Calendário Interativo
- Componentes CalendarGrid, CalendarHeader, DayCell
- Visualização mensal com barra de atividades por tipo
- Seleção de múltiplos dias por clique
- DayDetailPanel lateral
- Modais de lançamento, lote e planejamento
- Indicadores visuais (feriado, consolidado, indisponível)

### JBT-11 — Relatórios e Exportações
- Exportação CSV de operadores sem lançamento
- Relatórios de capacidade e produção por período
- Relatório de inconsistências (lançamentos divergentes)

### JBT-12 — Otimizações de Performance (Fase 1)
- 14 índices nas tabelas KPI materializadas
- Cache-Control headers nos endpoints KPI (max-age=60, stale-while-revalidate=30)
- TanStack Query global: staleTime=30s, gcTime=5min, refetchOnWindowFocus=false
- Substituição de `except Exception: pass` por logging estruturado + HTTPException

### JBT-13 — Substituição de Identidade Visual
- Substituição do símbolo "CP" pelo logotipo DSG (escudo com fundo transparente)
- Atualização no TopNav, Login e favicon
- Ajustes tipográficos no logotipo textual

### JBT-14 — Correção de Encoding de Credenciais
- Fix de `UnicodeDecodeError` em credenciais com caracteres portugueses (ã, ç)
- `urllib.parse.quote_plus()` aplicado em todas as propriedades de URL do banco
- Compatível com `config.env` em cp1252 (Windows) e UTF-8 (Linux)

### JBT-15 — Filtro de Usuários Inativos
- Usuários com `ativo = FALSE` em `sap_snapshot.dgeo_usuario` excluídos:
  - Do endpoint `/usuarios` (lista de operadores)
  - Das queries de pizza/capacidade para "todos"
  - Das opções de agendas como possibilidade de lançamento

### JBT-16 — Gráfico de Pizza Corrigido para Todos os Operadores
- Cálculo correto da capacidade total para "todos" usando grade (operadores ativos × dias úteis)
- Fallback parametrizado via `parametro_capacidade.minutos_dia_util_default`
- 100% não alocado quando operador não tem nenhum lançamento no mês
- Capacidade base via `generate_series` de dias úteis + LEFT JOIN em `capacidade_dia`

### JBT-17 — Simplificação do Calendário
- Remoção dos botões de visualização Dia/Semana do `CalendarHeader`
- Calendário fixo em visão mensal em todas as páginas de agenda
- Interface mais limpa e focada

### JBT-18 — Dashboard Contextual por Bloco
- Card "Blocos SAP" exibe "1 / nome do bloco" quando filtro ativo
- Tooltip com texto completo ao hover nas linhas truncadas dos cards de bloco

---

## 14. Padrões de Engenharia Aplicados

### 14.1 SOLID

| Princípio | Aplicação no Sistema |
|-----------|---------------------|
| **S — Single Responsibility** | `AgendaService` cuida de lançamentos, `ConsolidacaoService` cuida de fechamento, `AuditService` cuida de log — nenhum serviço mistura responsabilidades |
| **O — Open/Closed** | Novos tipos de atividade são adicionados via banco (enum extensível), não via código |
| **L — Liskov Substitution** | Todos os repositórios implementam contratos que podem ser substituídos em testes |
| **I — Interface Segregation** | `SomenteAdmin` e `UsuarioLogado` são dependencies separadas — endpoints só dependem do que precisam |
| **D — Dependency Inversion** | Services recebem engines e repositórios por injeção; não instanciam diretamente |

### 14.2 Clean Code

- **Funções pequenas e com nome descritivo:** `_dias_uteis_do_mes()`, `_pizza_query()`, `_garantir_indices()`
- **Constantes nomeadas:** `MINUTOS_DIA_UTIL_DEFAULT = 360` em vez de magic numbers
- **Enumerações tipadas:** `FaixaMinuto`, `GrupoAtividade`, `CodigoAtividade` em vez de strings livres
- **Comentários de intenção:** CTEs SQL com nome descritivo (`dias_uteis`, `grade`, `minuto_padrao`)
- **Sem código morto:** `em_uso=FALSE` para soft delete, sem colunas inutilizadas

### 14.3 Padrões de Resiliência

| Padrão | Implementação |
|--------|--------------|
| **Idempotência** | `INSERT ON CONFLICT DO UPDATE` em todo o pipeline sync |
| **Atomicidade** | Sync completo em transação única |
| **Cache** | TanStack Query com staleTime + Cache-Control HTTP |
| **Retry** | TanStack Query com `retry: 1` em falhas de rede |
| **Soft Delete** | `em_uso = FALSE` preserva histórico de lançamentos |
| **Auditoria** | Toda mutação registrada com antes/depois em JSONB |
| **Validação dupla** | Backend valida tudo (mesmo que o frontend já valide) |

### 14.4 Segurança

- JWT assinado com segredo de ambiente (não hardcoded)
- `ativo = TRUE` verificado no SAP antes de qualquer login
- Operadores não têm acesso a endpoints de outros usuários
- Credenciais de banco nunca expostas na URL (percent-encoded)
- Nenhum dado do SAP é modificado pelo sistema (somente leitura)

---

## 15. Ciclo de Desenvolvimento e Infraestrutura

### 15.1 Estrutura de Branches

```
main                    ← produção estável
feature/consolidado     ← branch de desenvolvimento ativo
```

### 15.2 Ambientes

| Ambiente | Host | Propósito |
|----------|------|-----------|
| Desenvolvimento | `C:\Desenvolvimento\capacidade_produtiva` | Servidor local de desenvolvimento |
| Worktree | `C:\Cartografia\...\worktrees\consolidado` | Branch de features ativas |

### 15.3 Execução do Backend

```bash
cd backend
uvicorn cp.main:app --reload --host 0.0.0.0 --port 8000
```

### 15.4 Execução do Frontend

```bash
cd frontend
npm run dev      # desenvolvimento (HMR)
npm run build    # build de produção (tsc + vite)
```

### 15.5 Migrações de Banco

```bash
cd backend
alembic upgrade head    # aplica todas migrações pendentes
alembic downgrade -1    # reverte última migração
```

### 15.6 Sincronização Manual via CLI

```bash
cd backend
python -m cp.cli.sync_sap    # executa pipeline completo de sync
```

---

## 16. Considerações Finais

### 16.1 O Poder do Sistema

O **Capacidade Produtiva** entrega algo que nenhuma planilha ou relatório SAP manual entrega: **a conexão direta entre o que foi planejado, o que foi realizado, e o que foi produzido no SAP** — tudo em uma única tela, com atualização a cada sincronização.

Para o gestor:
> "Eu sei, em tempo real, que dos 22 operadores, 14 estão acima de 70% do progresso esperado, 6 estão entre 35% e 70%, e 2 precisam de atenção. E sei exatamente quantas horas cada um trabalhou esta semana."

Para o operador:
> "Eu sei minha contribuição exata em cada bloco — quantos pontos acumulei como executor, como revisor, como corretor — e como evolui ao longo do tempo."

### 16.2 Escalabilidade Prevista

O design atual suporta:
- **Centenas de operadores** sem degradação (queries em tabelas materializadas)
- **Anos de histórico** sem impacto nas queries de KPI (dados pré-calculados)
- **Múltiplos projetos** e blocos em paralelo (filtros por bloco/subfase)

### 16.3 Próximos Passos Sugeridos (Backlog Técnico)

| Prioridade | Item |
|-----------|------|
| Alta | Code splitting com `React.lazy()` nos 12 routes do `App.tsx` |
| Alta | Refatoração do `Dashboard/index.tsx` (1.600 linhas) em 5 componentes |
| Alta | Refatoração do `kpi.py` (2.100 linhas) em 5 módulos |
| Média | SQL queries extraídas para `KpiQueryBuilder` |
| Média | URL params para filtros do dashboard (compartilhamento de estado) |
| Média | Logging estruturado JSON para observabilidade |
| Baixa | Refatoração do hook compartilhado AgendaPrevista/AgendaRealizada |
| Baixa | Testes de integração da camada de serviços |

---

*Documento elaborado com base na análise completa do código-fonte do repositório `EstevezCodando/capacidade_produtiva`, branch `feature/consolidado`.*
