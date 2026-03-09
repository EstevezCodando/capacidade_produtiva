"""Serviço de validação JWT.

Responsabilidade única: validar a assinatura do token e extrair os claims
do usuário. Não depende de FastAPI — pode ser usado em CLIs ou workers.

O serviço de autenticação (SAP) emite tokens com:
    - id           : int   — PK do usuário em sap.dgeo.usuario
    - uuid         : str   — identificador público do usuário
    - administrador: bool  — perfil de acesso
    - exp          : int   — expiração (5h a partir da emissão)

O header Authorization aceita dois formatos:
    Authorization: <token>
    Authorization: Bearer <token>
"""

from __future__ import annotations

import logging

import jwt
import jwt.exceptions

from cp.domain.usuario import UsuarioAutenticado

_logger = logging.getLogger(__name__)

# Algoritmo fixo — mesmo usado pelo serviço de autenticação SAP.
_ALGORITMO = "HS256"


class TokenInvalido(Exception):
    """Token ausente, expirado ou com assinatura inválida."""


def extrair_token(authorization: str | None) -> str:
    """Extrai o token bruto do header Authorization.

    Aceita:
        Authorization: eyJ...
        Authorization: Bearer eyJ...

    Raises:
        TokenInvalido: se o header estiver ausente ou vazio.
    """
    if not authorization:
        raise TokenInvalido("Header Authorization ausente.")
    partes = authorization.strip().split(" ", 1)
    # "Bearer <token>" ou apenas "<token>"
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1].strip()
    return partes[0].strip()


def validar_token(token: str, jwt_secret: str) -> UsuarioAutenticado:
    """Valida a assinatura e extrai os claims do token.

    Raises:
        TokenInvalido: se o token for inválido, expirado ou com claims faltando.
    """
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[_ALGORITMO])
    except jwt.exceptions.ExpiredSignatureError:
        raise TokenInvalido("Token expirado.")
    except jwt.exceptions.InvalidTokenError as exc:
        _logger.debug("Token inválido: %s", exc)
        raise TokenInvalido("Token inválido.") from exc

    try:
        usuario_id: int = int(payload["id"])
        usuario_uuid: str = str(payload["uuid"])
        administrador: bool = bool(payload.get("administrador", False))
    except (KeyError, ValueError, TypeError) as exc:
        raise TokenInvalido("Claims obrigatórios ausentes no token.") from exc

    return UsuarioAutenticado(
        usuario_id=usuario_id,
        usuario_uuid=usuario_uuid,
        administrador=administrador,
    )


def autenticar(authorization: str | None, jwt_secret: str) -> UsuarioAutenticado:
    """Pipeline completo: extrai token do header → valida → retorna contexto.

    Raises:
        TokenInvalido: em qualquer falha de autenticação.
    """
    token = extrair_token(authorization)
    return validar_token(token, jwt_secret)
