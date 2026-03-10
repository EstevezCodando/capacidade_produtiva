# Módulo de Agenda e Capacidade

## Visão Geral

Este módulo implementa a gestão de **Agenda e Capacidade** do sistema CapacidadeProdutiva, permitindo:

- Planejamento de alocação de tempo por usuário, dia e bloco
- Lançamento de tempo realizado (normal e hora extra)
- Controle de capacidade diária
- Gestão de feriados e indisponibilidades
- Consolidação de períodos
- Consultas analíticas

## Estrutura de Arquivos

```
src/cp/
├── domain/capacidade/
│   ├── __init__.py
│   ├── enums.py          # Enumerações de domínio
│   ├── exceptions.py     # Exceções específicas
│   ├── models.py         # Modelos SQLAlchemy
│   └── schemas.py        # Schemas Pydantic
├── repositories/capacidade/
│   ├── __init__.py
│   └── repositories.py   # Acesso a dados
├── services/capacidade/
│   ├── __init__.py
│   ├── agenda_service.py      # Gestão de planejamento e lançamentos
│   ├── audit_service.py       # Auditoria centralizada
│   ├── capacidade_service.py  # Parâmetros e cálculos
│   └── consolidacao_service.py # Consolidação de períodos
└── api/rotas/
    ├── agenda_v2.py      # Endpoints de agenda
    └── capacidade_v2.py  # Endpoints de capacidade
```

## Tabelas do Banco de Dados

Schema: `capacidade`

| Tabela | Descrição |
|--------|-----------|
| `tipo_atividade` | Catálogo de tipos (BLOCO, EXTERNA, AJUSTE, FERIAS, etc.) |
| `parametro_capacidade` | Parâmetros globais com vigência |
| `capacidade_dia` | Materialização diária por usuário |
| `agenda_prevista_admin` | Planejamento do administrador |
| `agenda_lancamento` | Lançamentos realizados |
| `feriado` | Cadastro de feriados |
| `indisponibilidade_usuario` | Indisponibilidades por usuário |
| `audit_log` | Log de auditoria |

## Regras de Negócio

### 1. Capacidade Normal vs Hora Extra

- **Capacidade Normal**: padrão de 360 min/dia útil (configurável)
- **Hora Extra**: minutos acima do limite diário
- Hora extra é contabilizada separadamente e não reduz ocioso

### 2. Limite de Capacidade

```
minutos_normais_bloco + minutos_normais_externa + minutos_normais_ajuste <= capacidade_normal_do_dia
```

Se exceder: erro 422

### 3. Permissões

**Operador pode:**
- Listar sua agenda e lançamentos
- Criar/editar/excluir lançamentos próprios (data ≤ hoje)
- Consultar sua capacidade

**Operador NÃO pode:**
- Lançar em data futura (erro 403)
- Acessar dados de outro usuário
- Alterar planejamento ou parâmetros

**Administrador pode:**
- Tudo que o operador pode
- Acessar dados de qualquer usuário
- Gerenciar planejamento
- Gerenciar feriados e indisponibilidades
- Consolidar períodos
- Alterar parâmetros de capacidade

### 4. Calendário

- **Fim de semana**: capacidade normal = 0 (hora extra permitida)
- **Feriado**: capacidade normal = 0 (hora extra permitida)
- **Indisponibilidade**: capacidade = 0, dia entra como "não alocado"

### 5. Consolidação

Status do dia:
- `ABERTO`: permite edições conforme perfil
- `CONSOLIDADO`: alteração requer admin + auditoria reforçada

### 6. Cálculo de Ocioso

```
minutos_ociosos = max(0, minutos_previstos_normais - (minutos_realizados_bloco_normais + minutos_perdidos_externas_normais))
```

Hora extra NÃO entra neste cálculo.

## API Endpoints

### Operador

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/agenda/meu-planejamento` | Agenda completa do usuário |
| GET | `/api/agenda/meus-lancamentos` | Lançamentos do usuário |
| POST | `/api/agenda/lancamento` | Criar lançamento |
| PUT | `/api/agenda/lancamento/{id}` | Editar lançamento |
| DELETE | `/api/agenda/lancamento/{id}` | Remover lançamento |
| GET | `/api/capacidade/meu-periodo` | Resumo analítico |

### Administrador

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/agenda/usuario/{id}` | Agenda de qualquer usuário |
| POST | `/api/agenda/planejamento` | Criar planejamento |
| PUT | `/api/agenda/planejamento/{id}` | Editar planejamento |
| DELETE | `/api/agenda/planejamento/{id}` | Remover planejamento |
| POST | `/api/agenda/lancamento-admin` | Lançamento para qualquer usuário |
| PUT | `/api/agenda/lancamento-admin/{id}` | Editar lançamento de qualquer usuário |
| DELETE | `/api/agenda/lancamento-admin/{id}` | Remover lançamento de qualquer usuário |
| POST | `/api/agenda/feriado` | Cadastrar feriado |
| DELETE | `/api/agenda/feriado/{id}` | Remover feriado |
| POST | `/api/agenda/indisponibilidade` | Cadastrar indisponibilidade |
| DELETE | `/api/agenda/indisponibilidade/{id}` | Remover indisponibilidade |
| GET | `/api/capacidade/config` | Configuração de teto |
| PUT | `/api/capacidade/config` | Atualizar teto |
| POST | `/api/capacidade/parametro` | Criar parâmetro |
| PUT | `/api/capacidade/parametro/{id}` | Atualizar parâmetro |
| GET | `/api/capacidade/status` | Status dos dias |
| POST | `/api/capacidade/consolidar-periodo` | Consolidar período |
| GET | `/api/capacidade/usuario/{id}` | Resumo de qualquer usuário |
| POST | `/api/capacidade/materializar` | Materializar capacidade |

## Migração

Executar a migração 0007:

```bash
cd backend
uv run alembic upgrade head
```

## Testes

Executar testes do módulo:

```bash
cd backend
uv run pytest tests/capacidade/ -v
```

## Auditoria

Todas as operações são auditadas na tabela `capacidade.audit_log`:

- Criação, edição e exclusão de planejamento
- Criação, edição e exclusão de lançamento
- Cadastro e remoção de feriado
- Cadastro e remoção de indisponibilidade
- Alteração de parâmetro de capacidade
- Consolidação de período

O log contém:
- Entidade e ID afetado
- Ação (CREATE, UPDATE, DELETE, CONSOLIDATE)
- Estado antes/depois (JSON)
- Usuário executor
- Timestamp

## Exemplos de Uso

### Criar lançamento (operador)

```http
POST /api/agenda/lancamento
Authorization: Bearer <token>
Content-Type: application/json

{
  "data": "2026-03-10",
  "bloco_id": 1,
  "tipo_atividade": "BLOCO",
  "faixa": "NORMAL",
  "minutos": 120,
  "descricao": "Trabalho em hidrografia"
}
```

### Consultar capacidade (operador)

```http
GET /api/capacidade/meu-periodo?data_inicio=2026-03-01&data_fim=2026-03-31
Authorization: Bearer <token>
```

Resposta:
```json
{
  "resumo": {
    "usuario_id": 2,
    "data_inicio": "2026-03-01",
    "data_fim": "2026-03-31",
    "minutos_previstos_normais": 7920,
    "minutos_realizados_bloco_normais": 6000,
    "minutos_perdidos_externas_normais": 500,
    "minutos_nao_alocados": 0,
    "minutos_ociosos": 1420,
    "minutos_extras_bloco": 120,
    "minutos_extras_externas": 30,
    "minutos_extras_totais": 150
  },
  "detalhes_por_dia": [...]
}
```

### Consolidar período (admin)

```http
POST /api/capacidade/consolidar-periodo
Authorization: Bearer <token_admin>
Content-Type: application/json

{
  "data_inicio": "2026-03-01",
  "data_fim": "2026-03-15",
  "usuarios_ids": [2, 3, 4],
  "ignorar_pendencias": false
}
```
