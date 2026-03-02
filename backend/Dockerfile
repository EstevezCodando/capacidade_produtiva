# Imagem base mínima e fixa para reprodutibilidade
FROM python:3.12-slim

WORKDIR /app

# Usuário não-root
RUN useradd -m appuser

# Copia arquivos de dependência primeiro para aproveitar cache
COPY pyproject.toml uv.lock README.md ./

# Instala uv com versão fixa
RUN pip install --no-cache-dir "uv==0.5.0"

# Define e cria o virtualenv do projeto
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv venv "$UV_PROJECT_ENVIRONMENT"

# Instala dependências de produção (sem dev)
RUN uv sync --frozen --no-dev

# Copia o código depois das dependências
COPY src ./src

# Imports a partir de src/
ENV PYTHONPATH=/app/src

# Garante que binários do venv sejam encontrados (uvicorn, etc.)
ENV PATH="/app/.venv/bin:$PATH"

# Troca para usuário não-root
USER appuser

# Executa uvicorn diretamente (o PATH já aponta para o venv)
CMD ["uvicorn", "cp.main:app", "--host", "0.0.0.0", "--port", "8000"]