# =============================================================================
# Stage 1 — builder
# Instala dependencias de producao num venv isolado.
# uv e mais rapido que pip e garante reproducibilidade via uv.lock.
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# uv precisa do lock file e do pyproject para resolver dependencias
COPY pyproject.toml uv.lock README.md ./

# Instala uv com versao fixa para reproducibilidade
RUN pip install --no-cache-dir "uv==0.5.21"

# Virtualenv explicito fora do projeto para copiar facilmente no stage final
ENV UV_PROJECT_ENVIRONMENT=/build/.venv

# Instala somente producao — sem dev (pytest, mypy, ruff)
RUN uv sync --frozen --no-dev


# =============================================================================
# Stage 2 — runtime
# Imagem final minima: nao contem uv, pip, build tools nem dependencias de dev.
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Usuario nao-root para seguranca em producao
RUN useradd --no-create-home --shell /usr/sbin/nologin appuser

# Copia apenas o venv pre-compilado do stage builder
COPY --from=builder /build/.venv /app/.venv

# Codigo da aplicacao
COPY src ./src

# Migrations — necessarias para alembic upgrade head dentro do container
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# PYTHONPATH aponta para src/ onde o pacote cp/ esta
ENV PYTHONPATH=/app/src

# Binarios do venv tem prioridade sobre os do sistema
ENV PATH="/app/.venv/bin:$PATH"

# Nao gerar .pyc desnecessarios no container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

# Porta padrao — sobrescrita pelo CP_API_PORT no Compose ou no run
EXPOSE 3050

# Comando padrao: sobe apenas a API.
# Em producao usa-se `uv run inicializar` via Compose para rodar
# o pipeline completo (migracoes + sync + API).
CMD ["uvicorn", "cp.main:app", "--host", "0.0.0.0", "--port", "3050"]
