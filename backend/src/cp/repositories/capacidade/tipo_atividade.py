"""Repositório de Tipo de Atividade."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.enums import CodigoAtividade
from cp.domain.capacidade.models import TipoAtividade


class TipoAtividadeRepository:
    """Repositório para tipos de atividade."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def buscar_por_codigo(self, codigo: CodigoAtividade) -> TipoAtividade | None:
        """Busca tipo de atividade padrão pelo código."""
        with Session(self._engine) as session:
            return session.execute(
                select(TipoAtividade).where(
                    and_(
                        TipoAtividade.codigo == codigo,
                        TipoAtividade.bloco_id.is_(None),
                    )
                )
            ).scalar_one_or_none()

    def buscar_por_bloco_id(self, bloco_id: int) -> TipoAtividade | None:
        """Busca o tipo de atividade vinculado a um bloco sincronizado."""
        with Session(self._engine) as session:
            return session.execute(
                select(TipoAtividade).where(TipoAtividade.bloco_id == bloco_id)
            ).scalar_one_or_none()

    def listar_todos(self) -> Sequence[TipoAtividade]:
        """Lista todos os tipos de atividade."""
        with Session(self._engine) as session:
            return session.execute(select(TipoAtividade)).scalars().all()

    def buscar_por_id(self, id: int) -> TipoAtividade | None:
        """Busca tipo de atividade pelo ID."""
        with Session(self._engine) as session:
            return session.get(TipoAtividade, id)

    def listar_configuraveis(self) -> Sequence[TipoAtividade]:
        """Lista tipos de atividade configuráveis para a agenda.

        Inclui tanto os tipos padrão quanto os vinculados a blocos, ordenando
        primeiro pelos vinculados a bloco e depois pelo nome.
        """
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(TipoAtividade)
                    .order_by(
                        TipoAtividade.bloco_id.is_(None),
                        TipoAtividade.nome,
                        TipoAtividade.id,
                    )
                )
                .scalars()
                .all()
            )

    def atualizar_cor(self, id: int, cor: str) -> TipoAtividade | None:
        """Atualiza a cor de um tipo de atividade."""
        with Session(self._engine) as session:
            tipo = session.get(TipoAtividade, id)
            if not tipo:
                return None
            tipo.cor = cor
            session.commit()
            session.refresh(tipo)
            return tipo
