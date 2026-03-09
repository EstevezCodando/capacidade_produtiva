"""Testes unitários do serviço de autenticação JWT.

Sem banco de dados, sem FastAPI — testa apenas a lógica de domínio:
  - extrair_token: parsing do header Authorization
  - validar_token: verificação de assinatura e extração de claims
  - autenticar: pipeline completo
"""

from __future__ import annotations

import time

import jwt
import pytest

from cp.infrastructure.auth import TokenInvalido, autenticar, extrair_token, validar_token

_SECRET = "segredo-de-teste"
_ALGORITMO = "HS256"


def _make_token(payload: dict, secret: str = _SECRET) -> str:
    return jwt.encode(payload, secret, algorithm=_ALGORITMO)


def _payload_valido(extra: dict | None = None) -> dict:
    base = {
        "id": 42,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "administrador": False,
        "exp": int(time.time()) + 18_000,  # 5 horas
    }
    if extra:
        base.update(extra)
    return base


# ---------------------------------------------------------------------------
# extrair_token
# ---------------------------------------------------------------------------


def test_extrair_token_sem_bearer() -> None:
    token = "eyJtoken"
    assert extrair_token(token) == "eyJtoken"


def test_extrair_token_com_bearer() -> None:
    assert extrair_token("Bearer eyJtoken") == "eyJtoken"


def test_extrair_token_bearer_case_insensitive() -> None:
    assert extrair_token("BEARER eyJtoken") == "eyJtoken"


def test_extrair_token_header_none() -> None:
    with pytest.raises(TokenInvalido, match="ausente"):
        extrair_token(None)


def test_extrair_token_header_vazio() -> None:
    with pytest.raises(TokenInvalido):
        extrair_token("")


# ---------------------------------------------------------------------------
# validar_token
# ---------------------------------------------------------------------------


def test_validar_token_valido() -> None:
    token = _make_token(_payload_valido())
    usuario = validar_token(token, _SECRET)
    assert usuario.usuario_id == 42
    assert usuario.usuario_uuid == "550e8400-e29b-41d4-a716-446655440000"
    assert usuario.administrador is False
    assert usuario.eh_admin is False


def test_validar_token_admin() -> None:
    token = _make_token(_payload_valido({"administrador": True}))
    usuario = validar_token(token, _SECRET)
    assert usuario.administrador is True
    assert usuario.eh_admin is True


def test_validar_token_expirado() -> None:
    payload = _payload_valido({"exp": int(time.time()) - 1})
    token = _make_token(payload)
    with pytest.raises(TokenInvalido, match="expirado"):
        validar_token(token, _SECRET)


def test_validar_token_assinatura_invalida() -> None:
    token = _make_token(_payload_valido(), secret="outro-segredo")
    with pytest.raises(TokenInvalido, match="inválido"):
        validar_token(token, _SECRET)


def test_validar_token_claim_id_ausente() -> None:
    payload = _payload_valido()
    del payload["id"]
    token = _make_token(payload)
    with pytest.raises(TokenInvalido, match="Claims"):
        validar_token(token, _SECRET)


def test_validar_token_claim_uuid_ausente() -> None:
    payload = _payload_valido()
    del payload["uuid"]
    token = _make_token(payload)
    with pytest.raises(TokenInvalido, match="Claims"):
        validar_token(token, _SECRET)


def test_validar_token_administrador_ausente_default_false() -> None:
    """Claim administrador é opcional — default False."""
    payload = _payload_valido()
    del payload["administrador"]
    token = _make_token(payload)
    usuario = validar_token(token, _SECRET)
    assert usuario.administrador is False


# ---------------------------------------------------------------------------
# autenticar (pipeline completo)
# ---------------------------------------------------------------------------


def test_autenticar_com_bearer() -> None:
    token = _make_token(_payload_valido())
    usuario = autenticar(f"Bearer {token}", _SECRET)
    assert usuario.usuario_id == 42


def test_autenticar_sem_bearer() -> None:
    token = _make_token(_payload_valido())
    usuario = autenticar(token, _SECRET)
    assert usuario.usuario_id == 42


def test_autenticar_sem_header() -> None:
    with pytest.raises(TokenInvalido):
        autenticar(None, _SECRET)
