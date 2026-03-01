
# python:3.12-slim é a imagem oficial mínima.
# Não usar :latest — versão fixa garante reprodutibilidade.
FROM python:3.12-slim

WORKDIR /app

# Cria usuário não-root antes de qualquer COPY.
# Rodar como root em container é risco de segurança:
# se houver exploração, o atacante ganha root no host em configurações padrão.
RUN useradd -m appuser

# Copia apenas os arquivos de dependência primeiro.
# Motivo: Docker cacheia cada layer. Se só o código mudar (não o pyproject),
# o `uv sync` não roda de novo — o build fica muito mais rápido.
COPY pyproject.toml uv.lock README.md ./

# Instala uv e sincroniza dependências com lock file.
# --frozen: recusa instalar se uv.lock divergir do pyproject.toml
# --no-dev: não instala pytest, ruff, mypy em produção
RUN pip install uv && uv sync --frozen --no-dev

# Copia o código-fonte depois das dependências (cache mais eficiente)
COPY src ./src

# Copia o bootstrap de configuração.
# O operador pode executar dentro do container com:
#   docker run --rm -it capacidade-prod-backend python create_config.py
# O arquivo usa apenas stdlib + psycopg2-binary (já nas deps de produção).
COPY create_config.py ./

# PYTHONPATH aponta para src/ para que `import cp` funcione
# mesmo sem `uv pip install -e .` dentro do container.
ENV PYTHONPATH=/app/src

# Troca para usuário não-root
USER appuser

# Entrypoint: uvicorn serve a aplicação FastAPI.
# --host 0.0.0.0 é obrigatório em container — 127.0.0.1 não é acessível de fora.
CMD ["uv", "run", "uvicorn", "cp.main:app", "--host", "0.0.0.0", "--port", "8000"]