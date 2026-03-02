from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _database_exists(engine: Engine, db_name: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        )
        return result.scalar() is not None


def _create_database(engine: Engine, db_name: str) -> None:
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(text(f'CREATE DATABASE "{db_name}"'))


def criar_banco_se_necessario(
    host: str,
    port: int,
    usuario_admin: str,
    senha_admin: str,
    nome_banco: str,
) -> bool:
    admin_dsn = f"postgresql+psycopg2://{usuario_admin}:{senha_admin}@{host}:{port}/postgres"
    engine = create_engine(admin_dsn, future=True)

    if _database_exists(engine, nome_banco):
        return False

    _create_database(engine, nome_banco)
    return True
