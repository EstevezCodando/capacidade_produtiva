# CapacidadeProdutiva — Explicação do Sistema

## 1. Propósito

O CapacidadeProdutiva é uma plataforma web de gestão operacional que une duas dimensões distintas:

**Produção** — lida do SAP. O progresso do projeto é medido em pontos, onde cada Unidade de Trabalho (UT) tem um valor fixo no campo `macrocontrole.unidade_trabalho.dificuldade`. O sistema não altera o SAP, apenas lê, valida, calcula KPI e distribui pontos conforme regras determinísticas.

**Capacidade** — gerida pelo próprio CapacidadeProdutiva. Mede disponibilidade de tempo por usuário atraves de duas agendas, agenda planejada confecionada pelo gerente e agenda realizada confecionada pelo usuario, com governança, auditoria e consolidação por dia.

Capacidade Produtiva tem por objetivo reunir dados para responder com precisão a distribuição de tempo empregado me cada processo produtivo.

---

## 2. Fontes de verdade

| Fonte               | Responsabilidade                                                             |
| ------------------- | ---------------------------------------------------------------------------- |
| SAP (PostgreSQL)    | Estrutura de produção: Projeto, Lote, Bloco, UT, Atividades, Etapas, Notas   |
| Serviço de Auth     | Usuários, perfis (Administrador / Operador) e autenticação JWT               |
| CapacidadeProdutiva | Agenda, planejamento, apontamento, feriados, férias, auditoria, consolidação |

O CapacidadeProdutiva mantém um **espelho (snapshot)** do SAP em seu próprio banco PostgreSQL — schema `sap_snapshot` — e calcula tudo a partir desse espelho, garantindo idempotência, rastreabilidade e performance previsível.
A UI nunca consulta o SAP diretamente.

---

## 3. Hierarquia operacional do SAP

```
Projeto → Lote → Bloco → Unidade de Trabalho (UT) → Atividades
```

### Tabelas relevantes

- `macrocontrole.projeto`
- `macrocontrole.lote` (`projeto_id`)
- `macrocontrole.bloco` (`lote_id`)
- `macrocontrole.unidade_trabalho` (`bloco_id`, `subfase_id`, `lote_id`, `dificuldade`, `disponivel`)
- `macrocontrole.atividade` (`etapa_id`, `unidade_trabalho_id`, `usuario_id`, `tipo_situacao_id`, `data_inicio`, `data_fim`, `observacao`)
- `macrocontrole.etapa` (`tipo_etapa_id`, `subfase_id`, `lote_id`, `ordem`)
- `macrocontrole.subfase`
- `dominio.tipo_etapa`
- `dominio.tipo_situacao`

### Domínio tipo_situacao

| id  | Nome           |
| --- | -------------- |
| 1   | Não iniciada   |
| 2   | Em execução    |
| 3   | Pausada        |
| 4   | Finalizada     |
| 5   | Não finalizada |

### Domínio tipo_etapa

| id  | Nome             |
| --- | ---------------- |
| 1   | Execução         |
| 2   | Revisão          |
| 3   | Correção         |
| 4   | Revisão/Correção |
| 5   | Revisão final    |

O KPI é consolidado nos seguintes ciclos:

O ciclo padrão 1: **Execução (tipo_situação: Finalizada) → Revisão (tipo_situação: Finalizada) → Correção (tipo_situação: Finalizada)**. Nota armazenada na atividade Correção.

O ciclo padrão 1.1: **Execução (tipo_situação: Não Finalizada) → ... → Execução (tipo_situação: Finalizada) → Revisão (tipo_situação: Finalizada) → Correção (tipo_situação: Finalizada)**. Nota armazenada na atividade Correção.

O ciclo padrão 1.2: **Execução (tipo_situação: Finalizada) → Revisão (tipo_situação: Não Finalizada) → ... → Revisão (tipo_situação: Finalizada) → Correção (tipo_situação: Finalizada)**. Nota armazenada na atividade Correção.

O ciclo padrão 1.3: **Execução (tipo_situação: Finalizada) → Revisão (tipo_situação: Finalizada) → Correção (tipo_situação: Não Finalizada) → ... → Correção (tipo_situação: Finalizada)**. Nota armazenada na atividade Correção.
E variantes

O ciclo alternativo 2: **Execução (tipo_situação: Finalizada) → Revisão/Correção (tipo_situação: Finalizada)**. Nota armazenada na atividade Revisão/Correção.

O ciclo alternativo 2.1: **Execução (tipo_situação: Não Finalizada) → ... → Execução (tipo_situação: Finalizada) → Revisão/Correção (tipo_situação: Finalizada)**. Nota armazenada na atividade Revisão/Correção.

O ciclo alternativo 2.2: **Execução (tipo_situação: Finalizada) → Revisão/Correção (tipo_situação: Não Finalizada) → ... → Revisão/Correção (tipo_situação: Finalizada)**. Nota armazenada na atividade Revisão/Correção.
E variantes

O ciclo alternativo 3: **Execução (tipo_situação: Finalizada) → Revisão (tipo_situação: Finalizada)**. Sem nota armazenada.

O ciclo alternativo 3.1: **Execução (tipo_situação: Não Finalizada) → ... → Execução (tipo_situação: Finalizada) → Revisão (tipo_situação: Finalizada)**. Sem nota armazenada.

O ciclo alternativo 3.2: **Execução (tipo_situação: Finalizada) → Revisão (tipo_situação: Não Finalizada) → ... → Revisão (tipo_situação: Finalizada)**. Sem nota armazenada.

---

## 4. Nota do revisor

A nota é registrada no campo `macrocontrole.atividade.observacao` da atividade de etapa_id **Correção** ou **Revisão/Correção** , no formato:

```
N; texto livre
```

Onde `N` é um dígito de 1 a 9.

O campo pode conter múltiplos segmentos separados por `|` (concatenação do SAP). O parser deve varrer os segmentos e encontrar a primeira ocorrência que case com `([1-9])\s*;\s*(.+)`.

**Validações obrigatórias:**

- Observação ausente, nula ou vazia → nota inválida → Notificação ao gerente → UT não distribui os pontos
- Sem separador `;` → nota inválida → Notificação ao gerente → UT não distribui os pontos
- Dígito fora de 1..9 → nota inválida → Notificação ao gerente → UT não distribui os pontos

---

Quando todas as atividades com mesma UT só tiverem etapa_id **execução → revisão**, não é problema de validação a ausencia de nota.

---

## 5. Ciclo vigente da UT (idempotente)

O SAP pode reabrir ciclos criando nova atividade (novo `id`) para a mesma UT. A atividade anterior pode ficar como "Não finalizada".

**Regra determinística de seleção:**
Para cada UT e cada tipo de etapa (Execução, Revisão, Correção, Correção/Revisão), a atividade vigente é a de **maior `id`** para a etapa canônica daquela UT. Se não for possível determinar sem ambiguidade, a UT é marcada como `INCONSISTENTE_CICLO`.

A etapa canônica por tipo é a de **menor `ordem`** para aquele par `(lote_id, subfase_id)`.

Se existirem múltiplas revisões, apenas a do ciclo vigente é considerada.

---

## 6. Estados da consolidação de atividades de mesma UT

| Estado                       | Condição                                                    |
| ---------------------------- | ----------------------------------------------------------- |
| `PENDENTE_EXECUCAO`          | Sem execução finalizada                                     |
| `PENDENTE_REVISAO`           | Execução ok, sem revisão finalizada                         |
| `PENDENTE_CORRECAO`          | Revisão ok com nota 1..8, sem correção finalizada           |
| `INCONSISTENTE_NOTA`         | Correção finalizada, mas nota ausente ou inválida           |
| `INCONSISTENTE_DIFICULDADE`  | `dificuldade = 0`                                           |
| `INCONSISTENTE_CICLO`        | Impossível determinar ciclo vigente                         |
| `UT BLOQUEADA`               | `disponivel = false`                                        |
| `CONCLUIDA_SEM_CORRECAO`     | Execução + Revisão finalizadas, sem correção vigente        |
| `CONCLUIDA_COM_N_Finalizada` | Ciclo completo da UT entanto alguma Atv em "Não finalizada" |
| `CONCLUIDA_COM_CORRECAO`     | Execução + Revisão + Correção finalizadas com nota válida   |

---

## 7. Regra de conclusão da UT

### Caso especial — sem correção

Condição: não existe atividade de correção vigente.

Requisitos: execução finalizada + revisão finalizada.

Distribuição fixa: **60% executor / 40% revisor**. Nota não compõe. Se existir nota nesse cenário, gerar alerta "nota indevida em UT sem correção".

O mesmo vale para o caso : Execução → Revisão/Correção

### Caso padrão — com correção

Condição: existe atividade de correção vigente.

Requisitos: execução finalizada + revisão finalizada + correção finalizada + nota válida na correção.

Se qualquer requisito falhar, a UT não conclui e não distribui pontos.

---

## 8. Distribuição de pontos (caso padrão)

**Pontos da UT** = `dificuldade` (inteiro > 0).

**Percentual do revisor** pela nota N:

```
Perc_Revisor = 0.4875 - (0.0375 × N)
```

Resultado: nota 1 → 45%, nota 9 → 15%.

**Piscina de tarefa** = `1 - Perc_Revisor`

**Distribuição da piscina de tarefa:**

| Cenário                   | Condição             | Executor          | Corretor |
| ------------------------- | -------------------- | ----------------- | -------- |
| A — autocorreção          | Executor == Corretor | 100% da piscina   | 0%       |
| B — correção por terceiro | Executor ≠ Corretor  | `Piscina × (N/9)` | restante |

---

## 9. KPI de progresso

```
Pontos totais do escopo   = Σ dificuldade das UTs do escopo
Pontos concluídos         = Σ dificuldade das UTs com status CONCLUIDA_*
Progresso percentual      = Pontos concluídos / Pontos totais
```

UTs com `dificuldade = 0` são inconsistências — não somam, não somem silenciosamente, geram alerta.

O KPI é sempre rederivado do snapshot. Nunca incrementado por delta. Se nascer nova atividade para uma UT, o progresso é recalculado e pode diminuir — isso gera diff e alerta.

---

## 10. Agenda (capacidade)

Cada minuto do dia pode pertencer a exatamente um bloco do SAP ou a uma atividade externa/indisponibilidade.
Um dia pode ter múltiplos blocos.

### Regras base

| Regra                   | Detalhe                                            |
| ----------------------- | -------------------------------------------------- |
| Teto normal             | Configurado por dia (ex.: 6h úteis)                |
| Teto extra              | Máximo 10h além do expediente                      |
| Fim de semana / Feriado | Apenas extra permitido                             |
| Férias / Licença        | Normal bloqueado, extra permitido com alerta       |
| Dia futuro              | Bloqueado para operador                            |
| Dia ABERTO              | Edição permitida com log                           |
| Dia CONSOLIDADO         | Normal bloqueado, apenas extra com alerta ao admin |

### Consolidação

O gerente seleciona um intervalo de datas, e roda processos de validação que verificam se todos os lançamentos foram feitos.
Ou seja, se todo usuario que estava previamente cadastrado lançou suas horas normais naquele intervalo de tempo.

A consolidação só ocorre se não houver pendências. Caso contrário, retorna lista organizada de usuários e dias pendentes.

O teto normal e o teto extra podem ser ajustados via interface pelo gerente, em configurações.

---

## 11. Schemas do banco auxiliar

| Schema          | Conteúdo                                                         |
| --------------- | ---------------------------------------------------------------- |
| `sap_snapshot`  | Espelho das tabelas do SAP                                       |
| `auth_snapshot` | Espelho mínimo do Auth (usuários, perfis)                        |
| `kpi`           | Fatos e estados calculados                                       |
| `agregacao`     | Agregações materializadas por bloco/subfase/usuário/atividade/ut |
| `agenda`        | Planejamento e apontamento de horas                              |
| `capacidade`    | Teto diário, status do dia, consolidação                         |
| `log`           | Auditoria, alertas e trilhas de execução                         |
| `dominio`       | Catálogos internos e enums                                       |

---

## 12. Pipeline de atualização

```
Ingestão SAP (a cada 30min em horário útil) (O tempo de ingestão pode ser ajustados via interface pelo gerente, em configurações, e poder ser feito com o botão "sincronizar SAP" no painel de configurações.)
    ↓
Sync Auth (usuários e perfis)
    ↓
Execução KPI (etapa canônica → ciclo vigente → estados → notas → pontos → agregações → diffs/alertas)
    ↓
API → UI
```

Todo endpoint relevante devolve `sap_snapshot_atualizado_em` e `kpi_calculado_em` para indicar staleness.

---

## 13. Tecnologias

| Camada         | Tecnologia                                             |
| -------------- | ------------------------------------------------------ |
| Backend        | Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic         |
| Jobs           | APScheduler (ou Celery Beat)                           |
| Banco auxiliar | PostgreSQL 14+                                         |
| Frontend       | React + TypeScript + TanStack Query + Recharts/ECharts |
| Infra          | Docker Compose                                         |
| Gestão deps    | uv                                                     |
| Auth           | JWT validado com chaves do serviço de Auth             |

---

## 14. Abas do sistema

| Aba               | Perfil   | Objetivo                                           |
| ----------------- | -------- | -------------------------------------------------- |
| Dashboard         | Ambos    | KPI de produção + capacidade por bloco             |
| Minha Agenda      | Operador | Apontamento, correções, pendências                 |
| Gerenciar Agendas | Admin    | Planejamento, feriados, consolidação               |
| Operadores        | Admin    | Cadastro, vínculos, resumo de pendências           |
| Blocos do Projeto | Ambos    | Progresso por bloco e subfase com travas           |
| Atividades        | Ambos    | Rastrear atividades, notas, distribuição de pontos |
| Exportar          | Ambos    | Relatórios de capacidade e produção                |
| Perfil            | Ambos    | Detalhes do perfil, no caso do Admin configurações |
