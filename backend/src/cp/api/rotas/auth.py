"""Rotas de autenticação.

Este módulo implementa o login seguindo o mesmo padrão do SAP:
1. Verifica se o usuário existe e está ativo no banco SAP (dgeo.usuario)
2. Valida credenciais no servico_autenticacao
3. Gera um token JWT próprio com o JWT_SECRET do CP
4. Retorna o token para o frontend

O CP NÃO usa o token do servico_autenticacao — ele gera seu próprio token,
assim como o SAP faz.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import jwt
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.infrastructure.http_client import http_post

router = APIRouter(tags=["Autenticação"])
_logger = logging.getLogger(__name__)

_ALGORITMO = "HS256"
_TOKEN_EXPIRA_EM_HORAS = 10


class LoginRequest(BaseModel):
    """Payload de login."""

    usuario: str
    senha: str


class LoginResponse(BaseModel):
    """Resposta de login bem-sucedido."""

    success: bool = True
    token: str
    uuid: str
    administrador: bool


def _buscar_usuario_no_sap(engine_sap: Engine, login: str) -> dict[str, Any] | None:
    """Busca usuário no banco SAP pelo login.

    Igual ao SAP (login_ctrl.js):
    SELECT id, uuid, administrador FROM dgeo.usuario WHERE login = $usuario and ativo IS TRUE

    Returns:
        Dict com id, uuid, administrador, nome, nome_guerra se encontrado
        None se não encontrado ou inativo
    """
    sql = text("""
        SELECT id, uuid, administrador, nome, nome_guerra
        FROM dgeo.usuario
        WHERE login = :login AND ativo IS TRUE
    """)
    with engine_sap.connect() as conn:
        result = conn.execute(sql, {"login": login})
        row = result.fetchone()
        if row:
            return {
                "id": row.id,
                "uuid": str(row.uuid),
                "administrador": bool(row.administrador),
                "nome": row.nome,
                "nome_guerra": row.nome_guerra,
            }
        return None


def _validar_credenciais_no_auth_server(auth_url: str, usuario: str, senha: str, aplicacao: str = "sap") -> bool:
    """Valida credenciais no servico_autenticacao.

    Igual ao SAP (authenticate_user.js):
    - Faz POST /api/login no servico_autenticacao
    - Retorna True se válido, False se inválido
    - Levanta exceção em caso de erro de conexão
    """
    endpoint = f"{auth_url}/api/login"
    payload = {"usuario": usuario, "senha": senha, "aplicacao": aplicacao}

    try:
        status_code, data = http_post(endpoint, payload)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erro ao conectar com servico_autenticacao: {exc}",
        ) from exc

    if status_code != 201:
        return False

    return bool(data.get("success", False))


def _gerar_token_jwt(usuario_id: int, usuario_uuid: str, administrador: bool, jwt_secret: str) -> str:
    """Gera token JWT próprio do CP.

    Igual ao SAP (login_ctrl.js signJWT):
    - Assina com o JWT_SECRET do CP
    - Expira em 10 horas
    """
    payload = {
        "id": usuario_id,
        "uuid": usuario_uuid,
        "administrador": administrador,
        "exp": int(time.time()) + (_TOKEN_EXPIRA_EM_HORAS * 3600),
    }
    return jwt.encode(payload, jwt_secret, algorithm=_ALGORITMO)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Autenticação de usuário",
    description=("Valida credenciais no servico_autenticacao e retorna um token JWT gerado pelo CP. Segue o mesmo padrão do SAP."),
)
def login(body: LoginRequest, request: Request) -> dict[str, Any]:
    """Login seguindo o padrão SAP.

    1. Verifica se usuário existe e está ativo no banco SAP
    2. Valida credenciais no servico_autenticacao
    3. Gera token JWT próprio com JWT_SECRET do CP
    4. Retorna token para o frontend
    """
    settings = request.app.state.settings
    auth_url = settings.auth_url.rstrip("/")
    jwt_secret = settings.jwt_secret
    engine_sap = request.app.state.engine_sap

    # 1. Verifica se usuário existe e está ativo no banco SAP
    # Igual ao SAP: primeiro verifica no banco local, depois no auth
    usuario_db = _buscar_usuario_no_sap(engine_sap, body.usuario)
    if not usuario_db:
        _logger.debug("Usuário não encontrado ou inativo no SAP: %s", body.usuario)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não autorizado para utilizar o sistema",
        )

    # 2. Valida credenciais no servico_autenticacao
    autenticado = _validar_credenciais_no_auth_server(auth_url, body.usuario, body.senha)
    if not autenticado:
        _logger.debug("Credenciais inválidas para: %s", body.usuario)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválida",
        )

    # Extrai dados do usuário do banco SAP
    usuario_id = usuario_db["id"]
    usuario_uuid = str(usuario_db["uuid"])
    administrador = bool(usuario_db["administrador"])

    # 3. Gera token JWT próprio do CP
    token = _gerar_token_jwt(usuario_id, usuario_uuid, administrador, jwt_secret)

    _logger.info("Login bem-sucedido: %s (id=%d, admin=%s)", body.usuario, usuario_id, administrador)

    # 4. Retorna resposta
    return {
        "success": True,
        "token": token,
        "uuid": usuario_uuid,
        "administrador": administrador,
    }
