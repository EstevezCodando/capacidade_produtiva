"""Testes do factory criar_auth_provider.

Verifica que o factory retorna o provider correto baseado no ambiente.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cp.infrastructure.auth_provider import (
    MockAuthProvider,
    RealAuthProvider,
    criar_auth_provider,
)


def test_criar_auth_provider_em_ambiente_test() -> None:
    """Em ENVIRONMENT=test, deve retornar MockAuthProvider."""
    settings = MagicMock()
    settings.environment = "test"
    settings.testing_mode = False
    settings.jwt_secret = "test-secret"
    settings.auth_url = None

    provider = criar_auth_provider(settings)

    assert isinstance(provider, MockAuthProvider)


def test_criar_auth_provider_com_testing_mode() -> None:
    """Com TESTING_MODE=true, deve retornar MockAuthProvider."""
    settings = MagicMock()
    settings.environment = "production"
    settings.testing_mode = True
    settings.jwt_secret = "test-secret"
    settings.auth_url = "http://auth.example.com"

    provider = criar_auth_provider(settings)

    assert isinstance(provider, MockAuthProvider)


def test_criar_auth_provider_em_producao() -> None:
    """Em produção (sem testing_mode), deve retornar RealAuthProvider."""
    settings = MagicMock()
    settings.environment = "production"
    settings.testing_mode = False
    settings.jwt_secret = "prod-secret"
    settings.auth_url = "http://auth.example.com:3010"

    provider = criar_auth_provider(settings)

    assert isinstance(provider, RealAuthProvider)


def test_criar_auth_provider_producao_sem_auth_url_falha() -> None:
    """Em produção sem AUTH_URL, deve levantar ValueError."""
    settings = MagicMock()
    settings.environment = "production"
    settings.testing_mode = False
    settings.jwt_secret = "prod-secret"
    settings.auth_url = None

    with pytest.raises(ValueError, match="AUTH_URL"):
        criar_auth_provider(settings)


def test_criar_auth_provider_local_sem_auth_url_falha() -> None:
    """Em local (não-test) sem AUTH_URL, deve levantar ValueError."""
    settings = MagicMock()
    settings.environment = "local"
    settings.testing_mode = False
    settings.jwt_secret = "local-secret"
    settings.auth_url = ""

    with pytest.raises(ValueError, match="AUTH_URL"):
        criar_auth_provider(settings)
