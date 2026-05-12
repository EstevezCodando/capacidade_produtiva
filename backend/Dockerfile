# =============================================================================
# Stage 1 — builder
# Instala dependências de produção num venv isolado.
# uv é mais rápido que pip e garante reprodutibilidade via uv.lock.
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

RUN pip install --no-cache-dir "uv==0.5.21"

# Mesmo path do runtime: shebangs dos entry points ficam corretos após COPY
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Somente produção — sem pytest, mypy, ruff
RUN uv sync --frozen --no-dev


# =============================================================================
# Stage 2 — runtime
# Imagem final mínima: sem uv, sem pip, sem ferramentas de build.
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# curl: usado pelo HEALTHCHECK no Compose
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Usuário não-root para segurança em produção
RUN useradd --no-create-home --shell /usr/sbin/nologin appuser

# Venv pré-compilado do stage builder (path idêntico → shebangs corretos)
COPY --from=builder /app/.venv /app/.venv

# Código da aplicação
COPY src ./src

# Migrations — necessárias para alembic upgrade head dentro do container
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Script de inicialização com pipeline: migrate → sync-sap → uvicorn
COPY entrypoint.sh /app/entrypoint.sh
# Garantir LF (o arquivo pode vir com CRLF do Windows)
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 3050

ENTRYPOINT ["/app/entrypoint.sh"]
