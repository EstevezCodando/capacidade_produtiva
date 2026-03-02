from __future__ import annotations

from typing import Self

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
            env_file=("config.env", ".env"),
            case_sensitive=False,
            extra="ignore",
        )


    environment: str = Field(default="production", alias="ENVIRONMENT")

    cp_api_port: int = Field(alias="CP_API_PORT")

    auth_url: str = Field(alias="AUTH_URL")
    auth_admin_user: str = Field(alias="AUTH_ADMIN_USER")
    auth_admin_password: str = Field(alias="AUTH_ADMIN_PASSWORD")

    cp_secret_key: str = Field(alias="CP_SECRET_KEY")

    cp_db_host: str = Field(alias="CP_DB_HOST")
    cp_db_port: int = Field(alias="CP_DB_PORT")
    cp_db_name: str = Field(alias="CP_DB_NAME")
    cp_db_user: str = Field(alias="CP_DB_USER")
    cp_db_password: str = Field(alias="CP_DB_PASSWORD")

    sap_db_host: str = Field(alias="SAP_DB_HOST")
    sap_db_port: int = Field(alias="SAP_DB_PORT")
    sap_db_name: str = Field(alias="SAP_DB_NAME")
    sap_db_user: str = Field(alias="SAP_DB_USER")
    sap_db_password: str = Field(alias="SAP_DB_PASSWORD")

    sap_test_db_host: str = Field(alias="SAP_TEST_DB_HOST")
    sap_test_db_port: int = Field(alias="SAP_TEST_DB_PORT")
    sap_test_db_name: str = Field(alias="SAP_TEST_DB_NAME")
    sap_test_db_user: str = Field(alias="SAP_TEST_DB_USER")
    sap_test_db_password: str = Field(alias="SAP_TEST_DB_PASSWORD")
    
    @classmethod
    def from_env(cls) -> Self:
        return cls()  # type: ignore[call-arg]
    @property
    def cp_db_url(self) -> str:
        return self.cp_dsn

    @property
    def sap_db_url(self) -> str:
        return self.sap_dsn

    @property
    def sap_test_db_url(self) -> str:
        return self.sap_test_dsn

    @property
    def cp_dsn(self) -> str:
        return f"postgresql+psycopg2://{self.cp_db_user}:{self.cp_db_password}" f"@{self.cp_db_host}:{self.cp_db_port}/{self.cp_db_name}"

    @property
    def sap_dsn(self) -> str:
        return f"postgresql+psycopg2://{self.sap_db_user}:{self.sap_db_password}" f"@{self.sap_db_host}:{self.sap_db_port}/{self.sap_db_name}"

    @property
    def sap_test_dsn(self) -> str:
        return (
            f"postgresql+psycopg2://{self.sap_test_db_user}:{self.sap_test_db_password}"
            f"@{self.sap_test_db_host}:{self.sap_test_db_port}/{self.sap_test_db_name}"
        )
