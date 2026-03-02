# CapacidadeProdutiva — Backend

Sistema de gestão operacional que une produção (SAP) e capacidade (agenda).

## Pré-requisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado
- Acesso ao banco PostgreSQL do SAP (somente leitura)
- Acesso ao Serviço de Autenticação em execução
- Arquivo `server/config.env` do SAP (para extrair o `JWT_SECRET`)

## Primeiro uso — configuração do ambiente

Antes de rodar a aplicação pela primeira vez é necessário gerar o arquivo
`server/config.env` com as credenciais do SAP e do Serviço de Autenticação.

```powershell
# 1. Entre na pasta do backend
cd backend

# 2. Instale as dependências (cria .venv automaticamente)
uv sync

# 3. Execute o assistente de configuração
uv run create-config
```

O assistente irá solicitar interativamente:

| Campo                                       | Descrição                              |
| ------------------------------------------- | -------------------------------------- |
| CP DB host / port / name / user / password  | Banco auxiliar do CapacidadeProdutiva  |
| SAP DB host / port / name / user / password | Banco do SAP (usuário somente leitura) |
| URL do Serviço de Autenticação              | Ex: `http://192.168.0.10:3010`         |
| Caminho para o `config.env` do SAP          | Para extrair o `JWT_SECRET`            |

Todas as flags também podem ser passadas diretamente (útil em automação):

```powershell
uv run create-config `
  --cp-db-host localhost --cp-db-port 5432 --cp-db-name capacidade_produtiva `
  --cp-db-user cp_user --cp-db-password **** `
  --sap-db-host [IP] --sap-db-port 5432 --sap-db-name sap `
  --sap-db-user sap_readonly --sap-db-password **** `
  --auth-server-url http://[IP]:3010 `
  --sap-config-env C:\sap\server\config.env
```

O script valida as conexões antes de gravar e, ao final, cria `server/config.env`.
Esse arquivo **não deve ser commitado** — já está no `.gitignore`.

Próximo passo após a configuração:

```powershell
uv run alembic upgrade head
```

## Comandos do dia a dia

```powershell
# Rodar testes com cobertura
uv run pytest

# Lint
uv run ruff check .

# Formatar código
uv run ruff format .

# Type check
uv run mypy src

# Rodar a aplicação
uv run uvicorn cp.main:app --reload
```

## Docker

```powershell
# Build
docker build -t capacidade-prod-backend .

# Rodar a aplicação
docker run -p 8000:8000 capacidade-prod-backend

# Rodar o assistente de configuração dentro do container
docker run --rm -it capacidade-prod-backend uv run create-config
```

## Estrutura do projeto

```
scripts/
  create_config.py  → assistente de configuração inicial (gera server/config.env)
src/cp/             → código-fonte do pacote instalável
  domain/           → entidades e regras de negócio (Sprint 2+)
  application/      → casos de uso (Sprint 2+)
  infrastructure/   → banco, SAP, auth (Sprint 2+)
  api/              → endpoints FastAPI (Sprint 3+)
  config/           → configurações e settings (Sprint 2+)
tests/
  scripts/          → testes do assistente de configuração
server/
  config.env        → gerado por create-config (não commitado)
```
