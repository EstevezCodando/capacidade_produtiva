from __future__ import annotations

from pathlib import Path

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.config.settings import Settings
from cp.infrastructure.db import criar_engine_cp, criar_engine_sap

_FIXTURES_DIR = Path(__file__).parent / "fixtures"

_SNAPSHOT_TABLES = [
    "macrocontrole_perfil_producao_operador",
    "macrocontrole_perfil_producao_etapa",
    "macrocontrole_perfil_producao",
    "macrocontrole_atividade",
    "macrocontrole_unidade_trabalho",
    "macrocontrole_etapa",
    "macrocontrole_bloco",
    "macrocontrole_lote",
    "macrocontrole_projeto",
    "macrocontrole_subfase",
    "macrocontrole_fase",
    "macrocontrole_linha_producao",
    "dgeo_usuario",
    "dominio_tipo_fase",
    "dominio_tipo_etapa",
    "dominio_tipo_situacao",
    "dominio_status",
]


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def engine_cp(settings: Settings) -> Engine:
    return criar_engine_cp(settings)


@pytest.fixture(scope="session")
def engine_sap(settings: Settings) -> Engine:
    return criar_engine_sap(settings)


@pytest.fixture()
def sap_seed(engine_cp: Engine, settings: Settings) -> None:
    """Limpa snapshot + SAP e repopula do zero antes de cada teste."""

    # 1. Limpa o snapshot no banco CP
    with engine_cp.begin() as conn:
        tables = ", ".join(f"sap_snapshot.{t}" for t in _SNAPSHOT_TABLES)
        conn.execute(text(f"TRUNCATE TABLE {tables}"))

    # 2. Executa o seed no banco SAP via cursor (suporta scripts multi-statement)
    sql = (_FIXTURES_DIR / "sap_seed.sql").read_text(encoding="utf-8")
    dsn = (
        f"host={settings.sap_test_db_host} port={settings.sap_test_db_port} "
        f"dbname={settings.sap_test_db_name} user={settings.sap_test_db_user} "
        f"password={settings.sap_test_db_password}"
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.cursor().execute(sql)
