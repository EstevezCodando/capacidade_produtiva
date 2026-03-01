# --- Estágio único por ora (multi-stage virá quando houver build de assets) ---

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

# PYTHONPATH aponta para src/ para que `import cp` funcione
# mesmo sem `uv pip install -e .` dentro do container.
ENV PYTHONPATH=/app/src

# Troca para usuário não-root
USER appuser

# Entrypoint: executa cp.main como módulo Python
CMD ["python", "-m", "cp.main"]
