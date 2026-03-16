"""Repositório de Indisponibilidades de Usuário."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.models import IndisponibilidadeUsuario


class IndisponibilidadeRepository:
    """Repositório para indisponibilidades de usuário."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def buscar_por_id(self, id: int) -> IndisponibilidadeUsuario | None:
        """Busca indisponibilidade pelo ID."""
        with Session(self._engine) as session:
            return session.get(IndisponibilidadeUsuario, id)

    def listar_por_usuario(self, usuario_id: int) -> Sequence[IndisponibilidadeUsuario]:
        """Lista todas as indisponibilidades do usuário."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(IndisponibilidadeUsuario)
                    .where(IndisponibilidadeUsuario.usuario_id == usuario_id)
                    .order_by(IndisponibilidadeUsuario.data_inicio)
                )
                .scalars()
                .all()
            )

    def listar_por_usuario_periodo(
        self, usuario_id: int, data_inicio: date, data_fim: date
    ) -> Sequence[IndisponibilidadeUsuario]:
        """Lista indisponibilidades do usuário que intersectam o período."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(IndisponibilidadeUsuario)
                    .where(
                        and_(
                            IndisponibilidadeUsuario.usuario_id == usuario_id,
                            IndisponibilidadeUsuario.data_inicio <= data_fim,
                            IndisponibilidadeUsuario.data_fim >= data_inicio,
                        )
                    )
                    .order_by(IndisponibilidadeUsuario.data_inicio)
                )
                .scalars()
                .all()
            )

    def buscar_para_data(
        self, usuario_id: int, data: date
    ) -> IndisponibilidadeUsuario | None:
        """Busca indisponibilidade vigente para o usuário na data."""
        with Session(self._engine) as session:
            return session.execute(
                select(IndisponibilidadeUsuario).where(
                    and_(
                        IndisponibilidadeUsuario.usuario_id == usuario_id,
                        IndisponibilidadeUsuario.data_inicio <= data,
                        IndisponibilidadeUsuario.data_fim >= data,
                    )
                )
            ).scalar_one_or_none()

    def verificar_sobreposicao(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        excluir_id: int | None = None,
    ) -> bool:
        """Verifica se há sobreposição com indisponibilidades existentes."""
        with Session(self._engine) as session:
            query = select(IndisponibilidadeUsuario).where(
                and_(
                    IndisponibilidadeUsuario.usuario_id == usuario_id,
                    IndisponibilidadeUsuario.data_inicio <= data_fim,
                    IndisponibilidadeUsuario.data_fim >= data_inicio,
                )
            )
            if excluir_id:
                query = query.where(IndisponibilidadeUsuario.id != excluir_id)
            return session.execute(query).scalar_one_or_none() is not None

    def criar(
        self,
        usuario_id: int,
        tipo_atividade_id: int,
        data_inicio: date,
        data_fim: date,
        descricao: str | None,
        criado_por: int,
    ) -> IndisponibilidadeUsuario:
        """Cria nova indisponibilidade."""
        with Session(self._engine) as session:
            indisponibilidade = IndisponibilidadeUsuario(
                usuario_id=usuario_id,
                tipo_atividade_id=tipo_atividade_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
                descricao=descricao,
                criado_por=criado_por,
            )
            session.add(indisponibilidade)
            session.commit()
            session.refresh(indisponibilidade)
            return indisponibilidade

    def remover(self, id: int) -> bool:
        """Remove indisponibilidade. Retorna True se removido."""
        with Session(self._engine) as session:
            indisponibilidade = session.get(IndisponibilidadeUsuario, id)
            if not indisponibilidade:
                return False
            session.delete(indisponibilidade)
            session.commit()
            return True
