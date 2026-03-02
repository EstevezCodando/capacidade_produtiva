# CapacidadeProdutiva Backend

Backend do CapacidadeProdutiva.

Responsável por manter um snapshot no schema `sap_snapshot` a partir do banco SAP, desacoplando leitura analítica do banco transacional.

O arquivo `config.env` é gerado localmente e **não deve ser commitado**.

## Pré-requisitos

Python 3.12, uv instalado, PostgreSQL acessível, acesso ao banco do SAP (somente leitura).

## Primeiro uso

Entre na pasta do backend.

```powershell
cd backend
```

Instale as dependências.

```powershell
uv sync
```

Execute o assistente principal de inicialização.

```powershell
uv run inicializar
```

Esse comando gera o `config.env` e pode criar o banco do CP (opcional).

Depois aplique as migrações.

```powershell
uv run alembic upgrade head
```

Em seguida, execute a sincronização do SAP para o snapshot do CP.

```powershell
uv run sincronizar-sap
```

## Fluxo normal de desenvolvimento

Rodar a aplicação.

```powershell
uv run uvicorn cp.main:app --reload
```

Rodar testes.

```powershell
uv run pytest
```

Lint.

```powershell
uv run ruff check .
```

Formatar código.

```powershell
uv run ruff format .
```

Type check.

```powershell
uv run mypy src
```

## Sobre o config.env

O arquivo fica em `backend/config.env`. Ele é lido pelo `Settings` e não deve ir para o git.

Exemplo mínimo para ambiente local.

```env
ENVIRONMENT=local

CP_DB_HOST=localhost
CP_DB_PORT=5432
CP_DB_NAME=cp_teste
CP_DB_USER=postgres
CP_DB_PASSWORD=postgres

SAP_DB_HOST=localhost
SAP_DB_PORT=5432
SAP_DB_NAME=sap
SAP_DB_USER=postgres
SAP_DB_PASSWORD=postgres

SAP_TEST_DB_HOST=localhost
SAP_TEST_DB_PORT=5432
SAP_TEST_DB_NAME=sap_test
SAP_TEST_DB_USER=postgres
SAP_TEST_DB_PASSWORD=postgres
```

O CI materializa um `config.env` temporário automaticamente apenas para testes. O CI não precisa de auth.

## Docker

Build da imagem, execute na pasta `backend`.

```powershell
docker build -t capacidade-prod-backend .
```

Rodar a aplicação.

```powershell
docker run -p 8000:8000 capacidade-prod-backend
```

O container não gera `config.env`. As variáveis devem ser fornecidas via `--env-file`, `-e`, Docker Compose ou secrets do deploy.

## Solução de problemas e limpeza de cache

Se aparecer erro de ambiente ou dependências inconsistentes, primeiro valide que você está no diretório `backend`.

### Limpar cache e recriar o ambiente uv

Remove o ambiente virtual e recria do zero.

```powershell
cd backend
Remove-Item -Recurse -Force .venv
uv sync
```

Se o `uv sync` reclamar de lock desatualizado, gere lock e sincronize.

```powershell
cd backend
uv lock
uv sync
```

### Limpar caches do uv e do pip

Em casos raros de download corrompido ou cache inconsistente.

```powershell
cd backend
uv cache clean
python -m pip cache purge
```

### Limpar artefatos do pytest e cobertura

```powershell
cd backend
Remove-Item -Recurse -Force .pytest_cache, .coverage, htmlcov -ErrorAction SilentlyContinue
```

### Resetar migrações em ambiente de teste

Se você apagou o banco ou criou do zero e ficou com estado de migração estranho, o correto é recriar o banco e rodar `alembic upgrade head`. Evite apagar `alembic_version` em ambiente real.

Para desenvolvimento local, se precisar limpar versão de migração manualmente.

```powershell
# Ajuste o caminho do psql conforme sua instalação
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d cp_teste -c "DELETE FROM alembic_version;"
uv run alembic upgrade head
```

### Limpar snapshot

Se o snapshot estiver inconsistente durante desenvolvimento, você pode truncar as tabelas do schema `sap_snapshot` e rodar `sincronizar-sap` novamente. Faça isso apenas em ambiente local ou de teste.

## Estrutura do projeto

```text
src/cp/
  domain/
  application/
  infrastructure/
  api/
  config/

tests/
  fixtures/
```

O snapshot do SAP é gravado no schema `sap_snapshot` do banco CP.
