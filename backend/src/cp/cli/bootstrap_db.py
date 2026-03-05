# caminho: cli/bootstrap_db.py

from __future__ import annotations

import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from cp.infrastructure.sap_sync.analytics_manager import garantir_views_analytics

_SCHEMAS_CP: tuple[str, ...] = (
    "sap_snapshot",
    "sap_analytics",
    "auth_snapshot",
    "kpi",
    "agregacao",
    "agenda",
    "capacidade",
    "log",
    "dominio",
)

_REGEX_NOME_BANCO = re.compile(r"^[A-Za-z0-9_]+$")


def _validar_nome_banco(nome_banco: str) -> None:
    if not _REGEX_NOME_BANCO.fullmatch(nome_banco):
        raise ValueError(f"Nome de banco inválido: {nome_banco!r}. Use apenas letras, números e underscore.")


def _database_exists(engine: Engine, db_name: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        )
        return result.scalar() is not None


def _create_database(engine: Engine, db_name: str) -> None:
    _validar_nome_banco(db_name)

    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(text(f'CREATE DATABASE "{db_name}"'))


def _criar_schemas_cp(engine_cp: Engine) -> None:
    ddl = "\n".join(f'CREATE SCHEMA IF NOT EXISTS "{schema}";' for schema in _SCHEMAS_CP)
    with engine_cp.begin() as conn:
        conn.execute(text(ddl))


def criar_banco(
    host: str,
    port: int,
    usuario_admin: str,
    senha_admin: str,
    nome_banco: str,
) -> bool:
    """Cria o banco se não existir. Retorna True se criou, False se já existia."""
    admin_dsn = f"postgresql+psycopg2://{usuario_admin}:{senha_admin}@{host}:{port}/postgres"
    engine_admin = create_engine(admin_dsn, future=True)

    if _database_exists(engine_admin, nome_banco):
        return False

    _create_database(engine_admin, nome_banco)
    return True


def criar_banco_cp(
    host: str,
    port: int,
    usuario_admin: str,
    senha_admin: str,
    nome_banco: str,
) -> bool:
    """Bootstrap do CP: garante banco, schemas iniciais e views analíticas (idempotente).

    Retorna True se o banco foi criado agora.
    Se o banco já existir, ainda assim garante os schemas/views e retorna False.
    """
    criado_agora = criar_banco(
        host=host,
        port=port,
        usuario_admin=usuario_admin,
        senha_admin=senha_admin,
        nome_banco=nome_banco,
    )

    _validar_nome_banco(nome_banco)

    dsn_cp = f"postgresql+psycopg2://{usuario_admin}:{senha_admin}@{host}:{port}/{nome_banco}"
    engine_cp = create_engine(dsn_cp, future=True)
    _criar_schemas_cp(engine_cp)
    garantir_views_analytics(engine_cp)

    return criado_agora
