# CapacidadeProdutiva — Backend

Sistema de gestão operacional que une produção (SAP) e capacidade (agenda).

## Pré-requisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado

## Setup inicial

```powershell
# 1. Entre na pasta do backend
cd backend

# 2. Instale as dependências (cria .venv automaticamente)
uv sync

# 3. Instale o pacote em modo editável
uv pip install -e .
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
uv run python -m cp.main
```

## Docker

```powershell
# Build
docker build -t capacidade-prod-backend .

# Run
docker run capacidade-prod-backend
```

## Estrutura do projeto

```
src/cp/           → código-fonte do pacote instalável
  domain/         → entidades e regras de negócio (Sprint 2+)
  application/    → casos de uso (Sprint 2+)
  infrastructure/ → banco, SAP, auth (Sprint 2+)
  api/            → endpoints FastAPI (Sprint 3+)
  config/         → configurações e settings (Sprint 2+)
tests/            → testes automatizados
```
