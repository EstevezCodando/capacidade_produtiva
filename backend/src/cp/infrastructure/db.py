from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from cp.config.settings import Settings


def criar_engine_cp(settings: Settings) -> Engine:
    """Engine SQLAlchemy para o banco auxiliar (CP).

    Banco sob nosso controle, então podemos ter um pool moderado para estabilidade e throughput.
    """
    return create_engine(
        settings.cp_db_url,
        pool_pre_ping=True,
        pool_size=settings.cp_pool_size,
        max_overflow=settings.cp_pool_max_overflow,
        pool_timeout=settings.cp_pool_timeout,
        connect_args={"connect_timeout": settings.cp_connect_timeout},
    )


def criar_engine_sap(settings: Settings) -> Engine:
    """Engine SQLAlchemy para o banco do SAP (produção).

    SAP é recurso compartilhado operacional. Pool deve ser conservador para não causar pressão no ambiente.
    """
    return create_engine(
        settings.sap_db_url,
        pool_pre_ping=True,
        pool_size=settings.sap_pool_size,
        max_overflow=settings.sap_pool_max_overflow,
        pool_timeout=settings.sap_pool_timeout,
        connect_args={"connect_timeout": settings.sap_connect_timeout},
    )


def criar_engine_sap_test(settings: Settings) -> Engine:
    """Engine SQLAlchemy para o banco do SAP usado em testes.

    Em geral roda local ou CI, então pode ser menos conservador que produção.
    """
    return create_engine(
        settings.sap_test_db_url,
        pool_pre_ping=True,
        pool_size=settings.sap_test_pool_size,
        max_overflow=settings.sap_test_pool_max_overflow,
        pool_timeout=settings.sap_test_pool_timeout,
        connect_args={"connect_timeout": settings.sap_test_connect_timeout},
    )
