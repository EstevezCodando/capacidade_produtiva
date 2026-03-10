"""Dependências FastAPI reutilizáveis.

Expõe as dependências de autenticação e autorização como callables
<<<<<<< HEAD
compatíveis com `Depends()`. A lógica de validação fica em infra.auth —
=======
compatíveis com `Depends()`. A lógica de validação fica em auth_provider —
>>>>>>> feature/front
aqui apenas traduzimos erros de domínio para respostas HTTP.

Uso:
    from cp.api.deps import UsuarioLogado, SomenteAdmin

    @router.get("/minha-rota")
    def rota(usuario: UsuarioLogado) -> ...:
        ...

    @router.get("/rota-admin")
    def rota_admin(usuario: SomenteAdmin) -> ...:
        ...
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

<<<<<<< HEAD
from cp.domain.usuario import UsuarioAutenticado
from cp.infrastructure.auth import TokenInvalido, autenticar


def _jwt_secret(request: Request) -> str:
    """Extrai jwt_secret das settings injetadas no estado da app."""
    return request.app.state.settings.jwt_secret  # type: ignore[no-any-return]
=======
from cp.infrastructure.auth_provider import (
    AuthProvider,
    TokenInvalido,
    UsuarioAutenticado,
    criar_auth_provider,
)


def _get_auth_provider(request: Request) -> AuthProvider:
    """Obtém ou cria o AuthProvider a partir do estado da app.

    O AuthProvider é criado uma vez no startup e reutilizado.
    Em testes, um MockAuthProvider pode ser injetado diretamente em app.state.
    """
    # Se já existe um provider injetado (ex: em testes), usa ele
    if hasattr(request.app.state, "auth_provider"):
        return request.app.state.auth_provider  # type: ignore[no-any-return]

    # Caso contrário, cria baseado nas settings
    settings = request.app.state.settings
    provider = criar_auth_provider(settings)
    request.app.state.auth_provider = provider
    return provider
>>>>>>> feature/front


def verify_login(
    authorization: Annotated[str | None, Header()] = None,
<<<<<<< HEAD
    jwt_secret: str = Depends(_jwt_secret),
=======
    auth_provider: AuthProvider = Depends(_get_auth_provider),
>>>>>>> feature/front
) -> UsuarioAutenticado:
    """Valida o JWT e injeta o contexto do usuário.

    Aceita header nos formatos:
        Authorization: <token>
        Authorization: Bearer <token>

    Raises 401 se o token estiver ausente ou inválido.
    """
    try:
<<<<<<< HEAD
        return autenticar(authorization, jwt_secret)
=======
        return auth_provider.validar_token(authorization or "")
>>>>>>> feature/front
    except TokenInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def verify_admin(
    usuario: UsuarioAutenticado = Depends(verify_login),
) -> UsuarioAutenticado:
    """Exige perfil administrador.

    Raises 403 se o usuário autenticado não for administrador.
    """
    if not usuario.eh_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return usuario


# Aliases tipados — uso limpo nos type hints dos controllers
UsuarioLogado = Annotated[UsuarioAutenticado, Depends(verify_login)]
SomenteAdmin = Annotated[UsuarioAutenticado, Depends(verify_admin)]
