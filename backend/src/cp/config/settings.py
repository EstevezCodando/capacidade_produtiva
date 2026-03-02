from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("config.env", ".env"),
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = Field(default="production", alias="ENVIRONMENT")

    # CP banco
    cp_db_host: str = Field(alias="CP_DB_HOST")
    cp_db_port: int = Field(alias="CP_DB_PORT")
    cp_db_name: str = Field(alias="CP_DB_NAME")
    cp_db_user: str = Field(alias="CP_DB_USER")
    cp_db_password: str = Field(alias="CP_DB_PASSWORD")

    # CP serviço
    cp_api_port: int = Field(default=3050, alias="CP_API_PORT")
    cp_secret_key: str = Field(default="dev-secret", alias="CP_SECRET_KEY")

    # SAP produção
    sap_db_host: str = Field(alias="SAP_DB_HOST")
    sap_db_port: int = Field(alias="SAP_DB_PORT")
    sap_db_name: str = Field(alias="SAP_DB_NAME")
    sap_db_user: str = Field(alias="SAP_DB_USER")
    sap_db_password: str = Field(alias="SAP_DB_PASSWORD")

    # SAP teste
    sap_test_db_host: str = Field(default="localhost", alias="SAP_TEST_DB_HOST")
    sap_test_db_port: int = Field(default=5432, alias="SAP_TEST_DB_PORT")
    sap_test_db_name: str = Field(default="sap_test", alias="SAP_TEST_DB_NAME")
    sap_test_db_user: str = Field(default="postgres", alias="SAP_TEST_DB_USER")
    sap_test_db_password: str = Field(default="postgres", alias="SAP_TEST_DB_PASSWORD")

    # Auth opcional
    auth_url: str | None = Field(default=None, alias="AUTH_URL")
    auth_admin_user: str | None = Field(default=None, alias="AUTH_ADMIN_USER")
    auth_admin_password: str | None = Field(default=None, alias="AUTH_ADMIN_PASSWORD")

    @classmethod
    def from_env(cls) -> Self:
        return cls()  # type: ignore[call-arg]

    @model_validator(mode="after")
    def _validar_producao(self) -> Self:
        if self.environment.lower() == "production":
            if self.cp_secret_key == "dev-secret":
                raise ValueError("CP_SECRET_KEY deve ser definido em produção.")
            if not self.auth_url:
                raise ValueError("AUTH_URL deve ser definido em produção.")
            if not self.auth_admin_user or not self.auth_admin_password:
                raise ValueError(
                    "AUTH_ADMIN_USER e AUTH_ADMIN_PASSWORD devem ser definidos em produção."
                )
        return self

    @property
    def cp_db_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.cp_db_user}:{self.cp_db_password}"
            f"@{self.cp_db_host}:{self.cp_db_port}/{self.cp_db_name}"
        )

    @property
    def sap_db_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.sap_db_user}:{self.sap_db_password}"
            f"@{self.sap_db_host}:{self.sap_db_port}/{self.sap_db_name}"
        )

    @property
    def sap_test_db_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.sap_test_db_user}:{self.sap_test_db_password}"
            f"@{self.sap_test_db_host}:{self.sap_test_db_port}/{self.sap_test_db_name}"
        )