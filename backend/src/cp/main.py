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
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from cp.api.rotas import health, usuarios
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
)

# ---------------------------------------------------------------------------
# Routers
#
# Convenção de prefixo e proteção:
#   /health          — público
#   /usuarios/me     — autenticado (operador ou admin)
#   /usuarios        — somente admin
#   /kpis/**         — autenticado (a implementar)
#   /relatorios/**   — autenticado (a implementar)
# ---------------------------------------------------------------------------

app.include_router(health.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
