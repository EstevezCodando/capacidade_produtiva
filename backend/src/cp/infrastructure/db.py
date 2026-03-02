from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from cp.config.settings import Settings


def criar_engine_cp(settings: Settings) -> Engine:
    return create_engine(settings.cp_db_url, pool_pre_ping=True)


def criar_engine_sap(settings: Settings) -> Engine:
    return create_engine(settings.sap_db_url, pool_pre_ping=True)


def criar_engine_sap_test(settings: Settings) -> Engine:
    return create_engine(settings.sap_test_db_url, pool_pre_ping=True)
