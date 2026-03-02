from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfigEnv:
    cp_db_host: str
    cp_db_port: int
    cp_db_name: str
    cp_db_user: str
    cp_db_password: str
    cp_api_port: int

    sap_db_host: str
    sap_db_port: int
    sap_db_name: str
    sap_db_user: str
    sap_db_password: str

    auth_url: str
    auth_admin_user: str
    auth_admin_password: str

    incluir_sap_test: bool
    sap_test_db_host: str
    sap_test_db_port: int
    sap_test_db_name: str
    sap_test_db_user: str
    sap_test_db_password: str

    environment: str = "local"


def gerar_secret_key() -> str:
    return secrets.token_urlsafe(48)


def escrever_config_env(caminho: Path, cfg: ConfigEnv) -> None:
    cp_secret_key = gerar_secret_key()

    conteudo = f"""ENVIRONMENT={cfg.environment}

CP_DB_HOST={cfg.cp_db_host}
CP_DB_PORT={cfg.cp_db_port}
CP_DB_NAME={cfg.cp_db_name}
CP_DB_USER={cfg.cp_db_user}
CP_DB_PASSWORD={cfg.cp_db_password}

CP_API_PORT={cfg.cp_api_port}

SAP_DB_HOST={cfg.sap_db_host}
SAP_DB_PORT={cfg.sap_db_port}
SAP_DB_NAME={cfg.sap_db_name}
SAP_DB_USER={cfg.sap_db_user}
SAP_DB_PASSWORD={cfg.sap_db_password}

AUTH_URL={cfg.auth_url}
AUTH_ADMIN_USER={cfg.auth_admin_user}
AUTH_ADMIN_PASSWORD={cfg.auth_admin_password}

CP_SECRET_KEY={cp_secret_key}
"""

    if cfg.incluir_sap_test:
        conteudo += f"""
SAP_TEST_DB_HOST={cfg.sap_test_db_host}
SAP_TEST_DB_PORT={cfg.sap_test_db_port}
SAP_TEST_DB_NAME={cfg.sap_test_db_name}
SAP_TEST_DB_USER={cfg.sap_test_db_user}
SAP_TEST_DB_PASSWORD={cfg.sap_test_db_password}
"""

    caminho.write_text(conteudo, encoding="utf-8")
