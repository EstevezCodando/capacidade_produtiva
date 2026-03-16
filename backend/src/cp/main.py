"""Ponto de entrada do CapacidadeProdutiva.

Responsabilidades deste módulo:
  - Criar a aplicação FastAPI com lifespan (inicialização e encerramento).
  - Configurar logging estruturado.
  - Montar os routers da API.
  - Injetar Settings e Engines no estado da app (app.state) para
    que as dependências acessem sem importações globais.

A lógica de negócio não fica aqui — fica em dominio/, repositorios/ e
é invocada pelos controllers em api/rotas/.
"""

from __future__ import annotations

import logging
import logging.config
import pathlib
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from cp.api.rotas import (
    agenda,
    atividades,
    auth,
    capacidade,
    health,
    kpi,
    log,
    relatorios,
    sync,
    usuarios,
)
from cp.config.settings import Settings
from cp.infrastructure.db import criar_engine_cp, criar_engine_sap

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_CONFIG: dict[str, object] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "cp": {"level": "DEBUG", "propagate": True},
        "uvicorn.access": {"level": "WARNING"},
    },
}

logging.config.dictConfig(_LOG_CONFIG)
_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — inicialização e encerramento controlados
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configura recursos na subida e libera no encerramento."""
    settings = Settings.from_env()
    app.state.settings = settings
    app.state.engine_cp = criar_engine_cp(settings)
    app.state.engine_sap = criar_engine_sap(settings)
    _logger.info("CapacidadeProdutiva iniciando (env=%s)", settings.environment)
    try:
        yield
    finally:
        app.state.engine_cp.dispose()
        app.state.engine_sap.dispose()
        _logger.info("CapacidadeProdutiva encerrado.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CapacidadeProdutiva",
    description=("Backend que expõe KPIs, relatórios e pontuação operacional consumindo dados do SAP."),
    version="0.1.0",
    lifespan=_lifespan,
    # Swagger UI disponível em /api/docs  (ReDoc em /api/redoc)
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# Routers
#
# Convenção de prefixo e proteção:
#   /health             — público
#   /sync/**            — admin
#   /usuarios/**        — autenticado / admin
#   /kpi/**             — autenticado / admin
#   /atividades/**      — autenticado
#   /distribuicao-pontos — autenticado
#   /agenda/**          — autenticado / admin
#   /capacidade/**      — autenticado / admin
#   /relatorios/**      — autenticado
#   /log/**             — admin
# ---------------------------------------------------------------------------

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(kpi.router, prefix="/api")
app.include_router(atividades.router, prefix="/api")
app.include_router(agenda.router, prefix="/api")
app.include_router(capacidade.router, prefix="/api")
app.include_router(relatorios.router, prefix="/api")
app.include_router(log.router, prefix="/api")

# ---------------------------------------------------------------------------
# Documentação interativa — servida em /api-docs/
# Arquivos: backend/docs/{index.html, api.css, api.js}
# ---------------------------------------------------------------------------
# __file__ = src/cp/main.py → parent = src/cp → ×2 = src → ×3 = backend
_docs_dir = pathlib.Path(__file__).parent.parent.parent / "docs"
if _docs_dir.exists():
    app.mount("/api-docs", StaticFiles(directory=str(_docs_dir), html=True), name="api-docs")
