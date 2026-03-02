FROM python:3.12-slim

WORKDIR /app

RUN useradd -m appuser

COPY pyproject.toml uv.lock README.md ./

ARG UV_VERSION=0.5.0

RUN pip install --no-cache-dir "uv==${UV_VERSION}"

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN mkdir -p /opt/venv && chown -R appuser:appuser /opt/venv /app

RUN uv sync --frozen --no-dev

COPY src ./src

ENV PYTHONPATH=/app/src

USER appuser

CMD ["uv", "run", "uvicorn", "cp.main:app", "--host", "0.0.0.0", "--port", "8000"]