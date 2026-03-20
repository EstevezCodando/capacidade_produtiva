from __future__ import annotations

from typing import Self
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("config.env", ".env"),
        # Sem env_file_encoding → usa o encoding do sistema (cp1252 no Windows,
        # UTF-8 no Linux). quote_plus() nos urls garante que qualquer caractere
        # especial nas credenciais seja % -encoded antes de chegar ao psycopg2.
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = Field(default="production", alias="ENVIRONMENT")

    # Modo de teste: quando True, usa MockAuthProvider ao invés de RealAuthProvider
    # Isso permite rodar testes no CI sem depender do servico_autenticacao
    testing_mode: bool = Field(default=False, alias="TESTING_MODE")

    # CP banco
    cp_db_host: str = Field(alias="CP_DB_HOST")
    cp_db_port: int = Field(alias="CP_DB_PORT")
    cp_db_name: str = Field(alias="CP_DB_NAME")
    cp_db_user: str = Field(alias="CP_DB_USER")
    cp_db_password: str = Field(alias="CP_DB_PASSWORD")

    # Pool CP (banco auxiliar, leitura e escrita)
    # cp_pool_size: quantidade de conexões fixas no pool (unidade: conexões)
    cp_pool_size: int = Field(default=10, alias="CP_POOL_SIZE")
    # cp_pool_max_overflow: conexões extras além do pool_size em pico (unidade: conexões)
    cp_pool_max_overflow: int = Field(default=10, alias="CP_POOL_MAX_OVERFLOW")
    # cp_pool_timeout: tempo máximo esperando conexão do pool (unidade: segundos)
    cp_pool_timeout: int = Field(default=30, alias="CP_POOL_TIMEOUT")
    # cp_connect_timeout: tempo máximo para conectar no banco (unidade: segundos)
    cp_connect_timeout: int = Field(default=5, alias="CP_CONNECT_TIMEOUT")

    # CP serviço
    cp_api_port: int = Field(default=3050, alias="CP_API_PORT")
    # Chave interna do CP — usada para assinar cookies de sessão, CSRF, etc.
    # Gerada automaticamente pelo `uv run configurar` e nunca compartilhada.
    cp_secret_key: str = Field(default="dev-secret", alias="CP_SECRET_KEY")
    # Chave do servico_autenticacao — o CP não a gera, apenas a recebe.
    # Deve ser idêntica ao JWT_SECRET do serviço de autenticação SAP para
    # que a verificação de assinatura dos tokens funcione corretamente.
    jwt_secret: str = Field(default="dev-secret", alias="JWT_SECRET")

    # SAP produção
    sap_db_host: str = Field(alias="SAP_DB_HOST")
    sap_db_port: int = Field(alias="SAP_DB_PORT")
    sap_db_name: str = Field(alias="SAP_DB_NAME")
    sap_db_user: str = Field(alias="SAP_DB_USER")
    sap_db_password: str = Field(alias="SAP_DB_PASSWORD")

    # Pool SAP produção (conservador, pois é recurso compartilhado)
    # sap_pool_size: quantidade de conexões fixas no pool (unidade: conexões)
    sap_pool_size: int = Field(default=2, alias="SAP_POOL_SIZE")
    # sap_pool_max_overflow: conexões extras além do pool_size em pico (unidade: conexões)
    sap_pool_max_overflow: int = Field(default=0, alias="SAP_POOL_MAX_OVERFLOW")
    # sap_pool_timeout: tempo máximo esperando conexão do pool (unidade: segundos)
    sap_pool_timeout: int = Field(default=10, alias="SAP_POOL_TIMEOUT")
    # sap_connect_timeout: tempo máximo para conectar no banco (unidade: segundos)
    sap_connect_timeout: int = Field(default=5, alias="SAP_CONNECT_TIMEOUT")

    # SAP teste
    sap_test_db_host: str = Field(default="localhost", alias="SAP_TEST_DB_HOST")
    sap_test_db_port: int = Field(default=5432, alias="SAP_TEST_DB_PORT")
    sap_test_db_name: str = Field(default="sap_test", alias="SAP_TEST_DB_NAME")
    sap_test_db_user: str = Field(default="postgres", alias="SAP_TEST_DB_USER")
    sap_test_db_password: str = Field(default="postgres", alias="SAP_TEST_DB_PASSWORD")

    # Pool SAP teste (pode ser mais permissivo em CI/local)
    # sap_test_pool_size: quantidade de conexões fixas no pool (unidade: conexões)
    sap_test_pool_size: int = Field(default=5, alias="SAP_TEST_POOL_SIZE")
    # sap_test_pool_max_overflow: conexões extras além do pool_size em pico (unidade: conexões)
    sap_test_pool_max_overflow: int = Field(default=5, alias="SAP_TEST_POOL_MAX_OVERFLOW")
    # sap_test_pool_timeout: tempo máximo esperando conexão do pool (unidade: segundos)
    sap_test_pool_timeout: int = Field(default=30, alias="SAP_TEST_POOL_TIMEOUT")
    # sap_test_connect_timeout: tempo máximo para conectar no banco (unidade: segundos)
    sap_test_connect_timeout: int = Field(default=5, alias="SAP_TEST_CONNECT_TIMEOUT")

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
            if self.jwt_secret == "dev-secret":
                raise ValueError("JWT_SECRET deve ser definido em produção.")
            if not self.auth_url:
                raise ValueError("AUTH_URL deve ser definido em produção.")
            if not self.auth_admin_user or not self.auth_admin_password:
                raise ValueError("AUTH_ADMIN_USER e AUTH_ADMIN_PASSWORD devem ser definidos em produção.")
        return self

    @property
    def cp_db_url(self) -> str:
        u, p = quote_plus(self.cp_db_user), quote_plus(self.cp_db_password)
        return f"postgresql+psycopg2://{u}:{p}@{self.cp_db_host}:{self.cp_db_port}/{self.cp_db_name}"

    @property
    def sap_db_url(self) -> str:
        u, p = quote_plus(self.sap_db_user), quote_plus(self.sap_db_password)
        return f"postgresql+psycopg2://{u}:{p}@{self.sap_db_host}:{self.sap_db_port}/{self.sap_db_name}"

    @property
    def sap_test_db_url(self) -> str:
        u, p = quote_plus(self.sap_test_db_user), quote_plus(self.sap_test_db_password)
        return (
            f"postgresql+psycopg2://{u}:{p}"
            f"@{self.sap_test_db_host}:{self.sap_test_db_port}/{self.sap_test_db_name}"
        )
