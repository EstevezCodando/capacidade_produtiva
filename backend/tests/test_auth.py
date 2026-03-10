"""Testes unitários do serviço de autenticação JWT.

Sem banco de dados, sem FastAPI — testa apenas a lógica de domínio:
  - _extrair_token_bruto: parsing do header Authorization
  - validar_token: verificação de assinatura e extração de claims
  - MockAuthProvider: autenticação em modo teste
  - RealAuthProvider: validação de tokens
"""

from __future__ import annotations

import time

import jwt
import pytest

from cp.infrastructure.auth_provider import (
    CredenciaisInvalidas,
    MockAuthProvider,
    RealAuthProvider,
    TokenInvalido,
    UsuarioAutenticado,
    _extrair_token_bruto,
)

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
# _extrair_token_bruto
# ---------------------------------------------------------------------------


def test_extrair_token_sem_bearer() -> None:
    token = "eyJtoken"
    assert _extrair_token_bruto(token) == "eyJtoken"


def test_extrair_token_com_bearer() -> None:
    assert _extrair_token_bruto("Bearer eyJtoken") == "eyJtoken"


def test_extrair_token_bearer_case_insensitive() -> None:
    assert _extrair_token_bruto("BEARER eyJtoken") == "eyJtoken"


def test_extrair_token_header_none() -> None:
    with pytest.raises(TokenInvalido, match="ausente"):
        _extrair_token_bruto(None)


def test_extrair_token_header_vazio() -> None:
    with pytest.raises(TokenInvalido):
        _extrair_token_bruto("")


# ---------------------------------------------------------------------------
# RealAuthProvider.validar_token
# ---------------------------------------------------------------------------


def test_validar_token_valido() -> None:
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    token = _make_token(_payload_valido())
    usuario = provider.validar_token(token)
    assert usuario.usuario_id == 42
    assert usuario.usuario_uuid == "550e8400-e29b-41d4-a716-446655440000"
    assert usuario.administrador is False
    assert usuario.eh_admin is False


def test_validar_token_admin() -> None:
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    token = _make_token(_payload_valido({"administrador": True}))
    usuario = provider.validar_token(token)
    assert usuario.administrador is True
    assert usuario.eh_admin is True


def test_validar_token_expirado() -> None:
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    payload = _payload_valido({"exp": int(time.time()) - 1})
    token = _make_token(payload)
    with pytest.raises(TokenInvalido, match="expirado"):
        provider.validar_token(token)


def test_validar_token_assinatura_invalida() -> None:
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    token = _make_token(_payload_valido(), secret="outro-segredo")
    with pytest.raises(TokenInvalido, match="inválido"):
        provider.validar_token(token)


def test_validar_token_claim_id_ausente() -> None:
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    payload = _payload_valido()
    del payload["id"]
    token = _make_token(payload)
    with pytest.raises(TokenInvalido, match="Claims"):
        provider.validar_token(token)


def test_validar_token_claim_uuid_ausente() -> None:
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    payload = _payload_valido()
    del payload["uuid"]
    token = _make_token(payload)
    with pytest.raises(TokenInvalido, match="Claims"):
        provider.validar_token(token)


def test_validar_token_administrador_ausente_default_false() -> None:
    """Claim administrador é opcional — default False."""
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    payload = _payload_valido()
    del payload["administrador"]
    token = _make_token(payload)
    usuario = provider.validar_token(token)
    assert usuario.administrador is False


# ---------------------------------------------------------------------------
# RealAuthProvider com prefixo Bearer
# ---------------------------------------------------------------------------


def test_validar_token_com_bearer() -> None:
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    token = _make_token(_payload_valido())
    usuario = provider.validar_token(f"Bearer {token}")
    assert usuario.usuario_id == 42


def test_validar_token_sem_bearer() -> None:
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    token = _make_token(_payload_valido())
    usuario = provider.validar_token(token)
    assert usuario.usuario_id == 42


def test_validar_token_sem_header() -> None:
    provider = RealAuthProvider(auth_url="http://dummy", jwt_secret=_SECRET)
    with pytest.raises(TokenInvalido):
        provider.validar_token("")


# ---------------------------------------------------------------------------
# MockAuthProvider
# ---------------------------------------------------------------------------


def test_mock_provider_autenticar_admin() -> None:
    """MockAuthProvider autentica usuário admin predefinido."""
    provider = MockAuthProvider(jwt_secret=_SECRET)
    resultado = provider.autenticar_usuario("admin", "admin123")
    assert resultado.administrador is True
    assert resultado.uuid == "00000000-0000-0000-0000-000000000001"
    assert resultado.token  # não vazio


def test_mock_provider_autenticar_operador() -> None:
    """MockAuthProvider autentica usuário operador predefinido."""
    provider = MockAuthProvider(jwt_secret=_SECRET)
    resultado = provider.autenticar_usuario("operador", "operador123")
    assert resultado.administrador is False
    assert resultado.uuid == "00000000-0000-0000-0000-000000000002"


def test_mock_provider_autenticar_credenciais_invalidas() -> None:
    """MockAuthProvider rejeita credenciais inválidas."""
    provider = MockAuthProvider(jwt_secret=_SECRET)
    with pytest.raises(CredenciaisInvalidas):
        provider.autenticar_usuario("admin", "senha_errada")


def test_mock_provider_validar_token_gerado() -> None:
    """Token gerado pelo MockAuthProvider é válido."""
    provider = MockAuthProvider(jwt_secret=_SECRET)
    resultado = provider.autenticar_usuario("admin", "admin123")
    usuario = provider.validar_token(resultado.token)
    assert usuario.usuario_id == 1
    assert usuario.administrador is True


def test_mock_provider_obter_dados_usuario() -> None:
    """MockAuthProvider retorna dados do usuário autenticado."""
    provider = MockAuthProvider(jwt_secret=_SECRET)
    resultado = provider.autenticar_usuario("admin", "admin123")
    dados = provider.obter_dados_usuario(resultado.token, resultado.uuid)
    assert dados.login == "admin"
    assert dados.nome == "Administrador Teste"


def test_mock_provider_verificar_disponibilidade() -> None:
    """MockAuthProvider sempre retorna disponível."""
    provider = MockAuthProvider()
    assert provider.verificar_disponibilidade() is True


# ---------------------------------------------------------------------------
# UsuarioAutenticado
# ---------------------------------------------------------------------------


def test_usuario_autenticado_eh_admin_true() -> None:
    usuario = UsuarioAutenticado(usuario_id=1, usuario_uuid="abc", administrador=True)
    assert usuario.eh_admin is True


def test_usuario_autenticado_eh_admin_false() -> None:
    usuario = UsuarioAutenticado(usuario_id=1, usuario_uuid="abc", administrador=False)
    assert usuario.eh_admin is False
