from __future__ import annotations

import logging
import logging.config
import os


def configurar_logging(nivel: str = "INFO", nivel_sql: str | None = None) -> None:
    """Configura logging do serviço.

    Centraliza formatação e níveis para API e CLI.
    """
    nivel_normalizado = (nivel or "INFO").upper()

    logging_config: dict[str, object] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "padrao": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "padrao",
                "stream": "ext://sys.stdout",
            }
        },
        "root": {
            "handlers": ["stdout"],
            "level": nivel_normalizado,
        },
        "loggers": {
            # Mantém logs do Uvicorn coerentes com o root.
            "uvicorn": {"level": nivel_normalizado, "propagate": True},
            "uvicorn.error": {"level": nivel_normalizado, "propagate": True},
            "uvicorn.access": {"level": nivel_normalizado, "propagate": True},
        },
    }

    logging.config.dictConfig(logging_config)

    if nivel_sql:
        nivel_sql_normalizado = nivel_sql.upper()
        logging.getLogger("sqlalchemy.engine").setLevel(nivel_sql_normalizado)
        logging.getLogger("sqlalchemy.pool").setLevel(nivel_sql_normalizado)
