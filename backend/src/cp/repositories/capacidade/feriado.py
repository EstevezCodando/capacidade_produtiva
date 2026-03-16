"""Repositório de Feriados."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.models import Feriado


class FeriadoRepository:
    """Repositório para feriados."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def buscar_por_id(self, id: int) -> Feriado | None:
        """Busca feriado pelo ID."""
        with Session(self._engine) as session:
            return session.get(Feriado, id)

    def buscar_por_data(self, data: date) -> Feriado | None:
        """Busca feriado pela data."""
        with Session(self._engine) as session:
            return session.execute(
                select(Feriado).where(Feriado.data == data)
            ).scalar_one_or_none()

    def listar_periodo(self, data_inicio: date, data_fim: date) -> Sequence[Feriado]:
        """Lista feriados no período."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(Feriado)
                    .where(and_(Feriado.data >= data_inicio, Feriado.data <= data_fim))
                    .order_by(Feriado.data)
                )
                .scalars()
                .all()
            )

    def listar_todos(self) -> Sequence[Feriado]:
        """Lista todos os feriados."""
        with Session(self._engine) as session:
            return (
                session.execute(select(Feriado).order_by(Feriado.data))
                .scalars()
                .all()
            )

    def criar(self, data: date, descricao: str, criado_por: int) -> Feriado:
        """Cria novo feriado."""
        with Session(self._engine) as session:
            feriado = Feriado(data=data, descricao=descricao, criado_por=criado_por)
            session.add(feriado)
            session.commit()
            session.refresh(feriado)
            return feriado

    def remover(self, id: int) -> bool:
        """Remove feriado. Retorna True se removido."""
        with Session(self._engine) as session:
            feriado = session.get(Feriado, id)
            if not feriado:
                return False
            session.delete(feriado)
            session.commit()
            return True

    def eh_feriado(self, data: date) -> bool:
        """Verifica se a data é feriado."""
        return self.buscar_por_data(data) is not None
