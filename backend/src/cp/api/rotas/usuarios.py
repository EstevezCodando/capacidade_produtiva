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
    uuid: str
    login: str
    nome: str
    nome_guerra: str | None
    administrador: bool
    usuario_id: int
    usuario_uuid: str


class UsuarioResumo(BaseModel):
    id: int
    nome: str
    nome_guerra: str | None


class UsuariosListResponse(BaseModel):
    itens: list[UsuarioResumo]


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


def _buscar_usuario_snapshot(engine_cp: Engine, usuario_id: int) -> dict[str, Any] | None:
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
    engine_cp = request.app.state.engine_cp
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

    return UsuarioMe(
        uuid=usuario.usuario_uuid,
        login=f"user_{usuario.usuario_id}",
        nome=f"Usuário {usuario.usuario_id}",
        nome_guerra=None,
        administrador=usuario.administrador,
        usuario_id=usuario.usuario_id,
        usuario_uuid=usuario.usuario_uuid,
    )


@router.get("", summary="Lista todos os usuários (admin)")
def listar_usuarios(_: SomenteAdmin, request: Request) -> list[UsuarioResumo]:
    engine_cp = request.app.state.engine_cp
    sql = text("""
        SELECT id, nome, nome_guerra
        FROM sap_snapshot.dgeo_usuario
        WHERE ativo = TRUE
        ORDER BY nome
    """)
    with engine_cp.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [
        UsuarioResumo(id=row.id, nome=row.nome, nome_guerra=row.nome_guerra)
        for row in rows
    ]


@router.get("/{usuario_id}", summary="Detalhe de um usuário")
def detalhe_usuario(usuario_id: int, request: Request, _: SomenteAdmin) -> UsuarioDetalhe:
    engine_cp = request.app.state.engine_cp
    sql = text("""
        SELECT id, nome, nome_guerra, TRUE AS ativo, administrador
        FROM sap_snapshot.dgeo_usuario
        WHERE id = :id
    """)
    with engine_cp.connect() as conn:
        row = conn.execute(sql, {"id": usuario_id}).fetchone()
    if row is None:
        return UsuarioDetalhe(
            id=usuario_id,
            nome="",
            nome_guerra=None,
            ativo=False,
            administrador=False,
            pontos_executor=0.0,
            pontos_revisor=0.0,
            pontos_corretor=0.0,
            pendencias_agenda=[],
        )
    return UsuarioDetalhe(
        id=row.id,
        nome=row.nome,
        nome_guerra=row.nome_guerra,
        ativo=bool(row.ativo),
        administrador=bool(row.administrador),
        pontos_executor=0.0,
        pontos_revisor=0.0,
        pontos_corretor=0.0,
        pendencias_agenda=[],
    )
