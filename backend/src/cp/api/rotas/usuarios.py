"""Rotas de usuário.

Política de autorização:
    GET /usuarios/me      — qualquer usuário autenticado (operador ou admin)
    GET /usuarios         — somente administradores
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from cp.api.deps import SomenteAdmin, UsuarioLogado

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioMe(BaseModel):
    usuario_id: int
    usuario_uuid: str
    administrador: bool


@router.get("/me", summary="Dados do usuário autenticado")
def me(usuario: UsuarioLogado) -> UsuarioMe:
    """Retorna o contexto do usuário extraído do JWT."""
    return UsuarioMe(
        usuario_id=usuario.usuario_id,
        usuario_uuid=usuario.usuario_uuid,
        administrador=usuario.administrador,
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
