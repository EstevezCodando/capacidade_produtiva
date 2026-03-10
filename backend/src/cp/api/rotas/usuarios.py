"""Rotas de usuário.

Política de autorização:
    GET /usuarios/me      — qualquer usuário autenticado (operador ou admin)
    GET /usuarios         — somente administradores
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.api.deps import SomenteAdmin, UsuarioLogado

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioMe(BaseModel):
    """Dados do usuário autenticado."""

    uuid: str
    login: str
    nome: str
    nome_guerra: str | None
    administrador: bool
    # Campos legados para compatibilidade
    usuario_id: int
    usuario_uuid: str


def _buscar_usuario_snapshot(engine_cp: Engine, usuario_id: int) -> dict[str, Any] | None:
    """Busca dados do usuário no sap_snapshot."""
    sql = text("""
        SELECT id, login, nome, nome_guerra, administrador, uuid
        FROM sap_snapshot.dgeo_usuario
        WHERE id = :id
    """)
    with engine_cp.connect() as conn:
        result = conn.execute(sql, {"id": usuario_id})
        row = result.fetchone()
        if row:
            return {
                "id": row.id,
                "login": row.login,
                "nome": row.nome,
                "nome_guerra": row.nome_guerra,
                "administrador": bool(row.administrador),
                "uuid": str(row.uuid),
            }
        return None


@router.get("/me", summary="Dados do usuário autenticado")
def me(usuario: UsuarioLogado, request: Request) -> UsuarioMe:
    """Retorna o contexto do usuário extraído do JWT e enriquecido com dados do banco."""
    engine_cp = request.app.state.engine_cp

    # Tenta buscar dados completos do snapshot
    dados = _buscar_usuario_snapshot(engine_cp, usuario.usuario_id)

    if dados:
        return UsuarioMe(
            uuid=dados["uuid"],
            login=dados["login"],
            nome=dados["nome"],
            nome_guerra=dados["nome_guerra"],
            administrador=dados["administrador"],
            usuario_id=dados["id"],
            usuario_uuid=dados["uuid"],
        )

    # Fallback: usa apenas os dados do JWT
    return UsuarioMe(
        uuid=usuario.usuario_uuid,
        login=f"user_{usuario.usuario_id}",
        nome=f"Usuário {usuario.usuario_id}",
        nome_guerra=None,
        administrador=usuario.administrador,
        usuario_id=usuario.usuario_id,
        usuario_uuid=usuario.usuario_uuid,
    )


@router.get(
    "",
    summary="Lista todos os usuários (admin)",
    description="Endpoint reservado para administradores. Operadores recebem 403.",
)
def listar_usuarios(usuario: SomenteAdmin) -> dict[str, str]:
    # Stub — implementação real virá com o repositório de usuários.
    # A autorização já foi verificada pela dependência SomenteAdmin.
    return {"detail": "endpoint reservado para implementação futura", "solicitado_por": usuario.usuario_uuid}


class UsuarioDetalhe(BaseModel):
    id: int
    nome: str
    nome_guerra: str | None
    ativo: bool
    administrador: bool
    pontos_executor: float
    pontos_revisor: float
    pontos_corretor: float
    pendencias_agenda: list[str]


@router.get(
    "/{usuario_id}",
    summary="Detalhe de um usuário",
    description="Dados completos do usuário: perfil, pontos acumulados por papel e pendências de agenda.",
)
def detalhe_usuario(usuario_id: int, _: SomenteAdmin) -> UsuarioDetalhe:
    # Stub — implementação real virá com repositório de usuários e kpi.pontos_usuario
    return UsuarioDetalhe(
        id=usuario_id,
        nome="",
        nome_guerra=None,
        ativo=True,
        administrador=False,
        pontos_executor=0.0,
        pontos_revisor=0.0,
        pontos_corretor=0.0,
        pendencias_agenda=[],
    )
