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
