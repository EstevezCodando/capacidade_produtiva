# CapacidadeProdutiva — Backend

Backend que expõe KPIs, relatórios e pontuação operacional, consumindo dados do SAP via snapshot em PostgreSQL.

## Visão geral

```
SAP (externo, read-only)
        │  sincronizar-sap
        ▼
  sap_snapshot  ──►  kpi.*  ──►  API /api/...
  (banco CP)
```

A API roda na porta **3050** e todas as rotas ficam sob o prefixo `/api`.

---

## Pré-requisitos

| Ferramenta | Versão mínima |
|------------|---------------|
| Python     | 3.12          |
| uv         | 0.5+          |
| Docker + Compose | qualquer versão recente |
| PostgreSQL | 16 (ou via Docker) |

Acesso de leitura ao banco SAP é obrigatório para o sync.

---

## Execução com Docker Compose (recomendado)

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com as credenciais reais
```

Variáveis obrigatórias no `.env`:

| Variável | Descrição |
|---|---|
| `CP_DB_PASSWORD` | Senha do banco CP (criado pelo Compose) |
| `SAP_DB_HOST` | Host do banco SAP externo |
| `SAP_DB_NAME` | Nome do banco SAP |
| `SAP_DB_USER` | Usuário SAP (somente leitura) |
| `SAP_DB_PASSWORD` | Senha do SAP |
| `JWT_SECRET` | Chave compartilhada com o serviço de autenticação |
| `AUTH_URL` | URL do serviço de autenticação |
| `AUTH_ADMIN_USER` | Usuário admin no serviço de auth |
| `AUTH_ADMIN_PASSWORD` | Senha do admin no serviço de auth |

Gerar um `JWT_SECRET` seguro:

```bash
openssl rand -base64 48
```

### 2. Subir

```bash
docker compose up --build
```

Na primeira execução, o serviço `backend` vai automaticamente:

1. Rodar os testes e verificações de qualidade (`check`)
2. Aplicar as migrações do banco CP (`alembic upgrade head`)
3. Sincronizar o snapshot do SAP (`sincronizar-sap`)
4. Subir a API em `http://localhost:3050`

### 3. Verificar

```bash
curl http://localhost:3050/api/health
# {"status":"ok"}
```

Documentação interativa: [http://localhost:3050/docs](http://localhost:3050/docs)

---

## Execução local (desenvolvimento)

### 1. Entrar na pasta do backend

```bash
cd backend
```

### 2. Instalar dependências

```bash
uv sync
```

### 3. Gerar o config.env interativamente

O assistente pergunta todos os parâmetros de conexão e cria o `config.env`:

```bash
uv run configurar
```

> **Nota:** O comando que antes se chamava `inicializar` passou a se chamar `configurar`.  
> O novo `inicializar` executa o pipeline completo (veja abaixo).

### 4. Aplicar migrações

```bash
uv run alembic upgrade head
```

### 5. Sincronizar o SAP

```bash
uv run sincronizar-sap
```

### 6. Subir a API

```bash
uv run uvicorn cp.main:app --reload --port 3050
```

### Ou: pipeline completo de uma vez

```bash
uv run inicializar
```

Executa na ordem: `check` → `alembic upgrade head` → `sincronizar-sap` → `uvicorn`.

---

## Rotas da API

| Método | Rota | Autenticação | Descrição |
|--------|------|---|---|
| `GET` | `/api/health` | — | Health check |
| `GET` | `/api/usuarios/me` | Token JWT | Dados do usuário autenticado |
| `GET` | `/api/usuarios` | Admin | Lista usuários (admin only) |

### Autenticação

O token JWT é emitido pelo serviço de autenticação SAP. Enviar no header:

```
Authorization: Bearer <token>
# ou sem prefixo:
Authorization: <token>
```

Respostas de erro:

| Código | Situação |
|--------|----------|
| 401 | Token ausente, inválido ou expirado |
| 403 | Rota restrita a administradores |

---

## Desenvolvimento

### Comandos úteis

```bash
# Verificacao completa (testes + lint + type-check)
uv run check

# Somente testes
uv run pytest

# Lint
uv run ruff check .

# Formatar
uv run ruff format .

# Type check
uv run mypy src
```

### Scripts disponíveis

| Comando | Descrição |
|---|---|
| `uv run configurar` | Assistente interativo para gerar `config.env` |
| `uv run inicializar` | Pipeline completo: check + migrações + sync + API |
| `uv run sincronizar-sap` | Sincroniza SAP → sap_snapshot |
| `uv run check` | Testes + lint + mypy |
| `uv run alembic upgrade head` | Aplica migrações pendentes |

---

## Estrutura do projeto

```
proj/
├── docker-compose.yml          # Stack completa (cp_db + backend)
├── .env.example                # Template de variáveis de ambiente
└── backend/
    ├── Dockerfile              # Multi-stage: builder + runtime
    ├── pyproject.toml
    ├── alembic/                # Migrações do banco CP
    └── src/cp/
        ├── api/
        │   ├── deps.py         # verifyLogin, verifyAdmin, aliases tipados
        │   └── rotas/          # Controllers (sem lógica de negócio)
        ├── domain/             # Modelos e regras de domínio
        ├── infrastructure/     # DB, auth JWT, sap_sync
        ├── application/        # Serviços de aplicação
        ├── config/             # Settings (pydantic-settings)
        └── cli/                # Entrypoints CLI
```

---

## Variáveis de ambiente completas

```env
ENVIRONMENT=production           # production | local

# Banco CP
CP_DB_HOST=cp_db
CP_DB_PORT=5432
CP_DB_NAME=capacidade_produtiva
CP_DB_USER=cp_user
CP_DB_PASSWORD=...
CP_API_PORT=3050

# Banco SAP (externo)
SAP_DB_HOST=...
SAP_DB_PORT=5432
SAP_DB_NAME=...
SAP_DB_USER=...
SAP_DB_PASSWORD=...

# Auth
JWT_SECRET=...                   # Mesma chave do serviço de autenticação
AUTH_URL=http://sap-auth:3001
AUTH_ADMIN_USER=...
AUTH_ADMIN_PASSWORD=...

# SAP de teste (dev/CI apenas)
SAP_TEST_DB_HOST=localhost
SAP_TEST_DB_PORT=5432
SAP_TEST_DB_NAME=sap_test
SAP_TEST_DB_USER=postgres
SAP_TEST_DB_PASSWORD=postgres
```

---

## Solução de problemas

### Limpar e recriar ambiente uv

```bash
cd backend
# Windows
Remove-Item -Recurse -Force .venv && uv sync
# Linux/macOS
rm -rf .venv && uv sync
```

### Resetar migrações em dev

```bash
# Apagar versão e reaplicar do zero
psql -U postgres -d capacidade_produtiva -c "DELETE FROM alembic_version;"
uv run alembic upgrade head
```

### Limpar snapshot inconsistente

Truncar e resincronizar (somente em dev/local):

```bash
psql -U postgres -d capacidade_produtiva -c "
  TRUNCATE sap_snapshot.macrocontrole_atividade,
           sap_snapshot.macrocontrole_unidade_trabalho
  CASCADE;
"
uv run sincronizar-sap
```
