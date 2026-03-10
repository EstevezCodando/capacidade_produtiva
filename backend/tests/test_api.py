"""Testes de integracao dos endpoints FastAPI.

Testa o comportamento HTTP real dos middlewares e controllers,
sem banco de dados — usa TestClient do FastAPI/Starlette.

Cobre os criterios de aceite do sprint:
  1. Sem token -> 401
  2. Token invalido -> 401
  3. Token valido injeta contexto -> 200
  4. Rota admin -> 403 para nao-admin
  5. Header funciona com e sem prefixo "Bearer"

Estrategia de isolamento:
  Criamos uma app FastAPI de teste sem lifespan, montando os mesmos
  routers da app de producao. Injetamos MockAuthProvider para que
  a autenticacao funcione sem servico_autenticacao externo.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cp.api.rotas import health, usuarios
from cp.config.settings import Settings
from cp.infrastructure.auth_provider import MockAuthProvider

_SECRET = "segredo-de-integracao"
_ALGORITMO = "HS256"


def _token(extra: dict | None = None) -> str:
    payload: dict = {
        "id": 7,
        "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "administrador": False,
        "exp": int(time.time()) + 18_000,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITMO)


@pytest.fixture()
def client() -> TestClient:
    """App de teste isolada — sem lifespan, sem banco, sem config.env.

    Cria uma FastAPI limpa com os mesmos routers da app de producao
    e injeta MockAuthProvider e settings mockadas diretamente no app.state.
    Isso garante que a autenticacao funcione independente de variaveis
    de ambiente ou servicos externos.
    """
    test_app = FastAPI()
    test_app.include_router(health.router)
    test_app.include_router(usuarios.router)

    # Mock settings com jwt_secret
    mock_settings = MagicMock(spec=Settings)
    mock_settings.jwt_secret = _SECRET
    mock_settings.environment = "test"
    test_app.state.settings = mock_settings

    # Injeta MockAuthProvider diretamente
    test_app.state.auth_provider = MockAuthProvider(jwt_secret=_SECRET)

    # Injeta um mock para a engine do banco
    test_app.state.engine_cp = MagicMock()

    # CRIAMOS UMA CLASSE SIMPLES PARA O MOCK (Evita o ValidationError do Pydantic)
    class MockRow:
        id = 7
        usuario_id = 7
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        usuario_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        administrador = False
        nome = "Usuário Teste"
        nome_guerra = "Teste"
        login = "teste.operador"

    mock_conn = MagicMock()
    mock_result = MagicMock()

    mock_result.fetchone.return_value = MockRow()
    mock_conn.execute.return_value = mock_result
    test_app.state.engine_cp.connect.return_value.__enter__.return_value = mock_conn

    with TestClient(test_app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# /health — publico
# ---------------------------------------------------------------------------


def test_health_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# /usuarios/me — autenticado
# ---------------------------------------------------------------------------


def test_me_sem_token_retorna_401(client: TestClient) -> None:
    r = client.get("/usuarios/me")
    assert r.status_code == 401


def test_me_token_invalido_retorna_401(client: TestClient) -> None:
    r = client.get("/usuarios/me", headers={"Authorization": "token.invalido"})
    assert r.status_code == 401


def test_me_token_expirado_retorna_401(client: TestClient) -> None:
    token = _token({"exp": int(time.time()) - 1})
    r = client.get("/usuarios/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_me_token_valido_sem_bearer(client: TestClient) -> None:
    """Formato: Authorization: <token> (sem prefixo Bearer)."""
    token = _token()
    r = client.get("/usuarios/me", headers={"Authorization": token})
    assert r.status_code == 200
    assert r.json()["usuario_id"] == 7


def test_me_token_valido_com_bearer(client: TestClient) -> None:
    """Formato: Authorization: Bearer <token>."""
    token = _token()
    r = client.get("/usuarios/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["usuario_id"] == 7
    assert body["usuario_uuid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert body["administrador"] is False


# ---------------------------------------------------------------------------
# /usuarios — somente admin
# ---------------------------------------------------------------------------


def test_usuarios_sem_token_retorna_401(client: TestClient) -> None:
    r = client.get("/usuarios")
    assert r.status_code == 401


def test_usuarios_operador_retorna_403(client: TestClient) -> None:
    """Operador autenticado mas nao-admin -> 403."""
    token = _token({"administrador": False})
    r = client.get("/usuarios", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_usuarios_admin_retorna_200(client: TestClient) -> None:
    """Admin recebe 200."""
    token = _token({"administrador": True})
    r = client.get("/usuarios", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
