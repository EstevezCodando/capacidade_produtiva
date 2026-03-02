from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/cp/config/settings.py → src/cp/config → src/cp → src → backend
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
_CONFIG_ENV = _BACKEND_DIR / "server" / "config.env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_CONFIG_ENV,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    cp_db_host: str
    cp_db_port: int
    cp_db_name: str
    cp_db_user: str
    cp_db_password: str

    sap_db_host: str
    sap_db_port: int
    sap_db_name: str
    sap_db_user: str
    sap_db_password: str

    sap_test_db_host: str
    sap_test_db_port: int
    sap_test_db_name: str
    sap_test_db_user: str
    sap_test_db_password: str

    @property
    def cp_db_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.cp_db_user}:{self.cp_db_password}"
            f"@{self.cp_db_host}:{self.cp_db_port}/{self.cp_db_name}"
        )

    @property
    def sap_db_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.sap_db_user}:{self.sap_db_password}"
            f"@{self.sap_db_host}:{self.sap_db_port}/{self.sap_db_name}"
        )

    @property
    def sap_test_db_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.sap_test_db_user}:{self.sap_test_db_password}"
            f"@{self.sap_test_db_host}:{self.sap_test_db_port}/{self.sap_test_db_name}"
        )
