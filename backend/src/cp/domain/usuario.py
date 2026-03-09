"""Modelo de domínio do usuário autenticado.

Representa o contexto extraído do JWT após validação.
Não depende de nenhuma camada de infra ou API — pode ser importado
livremente por serviços de domínio e repositórios.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Contexto do usuário injetado na request após validação do JWT.

    Campos extraídos diretamente dos claims do token:
        usuario_id   — claim "id"   (PK em sap.dgeo.usuario)
        usuario_uuid — claim "uuid" (identificador público)
        administrador — claim "administrador" (perfil de acesso)
    """

    usuario_id: int
    usuario_uuid: str
    administrador: bool

    @property
    def eh_admin(self) -> bool:
        return self.administrador
