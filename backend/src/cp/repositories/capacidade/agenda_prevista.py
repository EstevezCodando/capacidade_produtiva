"""Repositório de Agenda Prevista (planejamento)."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.models import AgendaPrevistaAdmin


class AgendaPrevistaRepository:
    """Repositório para planejamento de agenda."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def buscar_por_id(self, id: int) -> AgendaPrevistaAdmin | None:
        """Busca planejamento pelo ID."""
        with Session(self._engine) as session:
            return session.get(AgendaPrevistaAdmin, id)

    def listar_por_usuario_periodo(
        self, usuario_id: int, data_inicio: date, data_fim: date
    ) -> Sequence[AgendaPrevistaAdmin]:
        """Lista planejamentos do usuário no período."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(AgendaPrevistaAdmin)
                    .where(
                        and_(
                            AgendaPrevistaAdmin.usuario_id == usuario_id,
                            AgendaPrevistaAdmin.data >= data_inicio,
                            AgendaPrevistaAdmin.data <= data_fim,
                            AgendaPrevistaAdmin.em_uso.is_(True),
                        )
                    )
                    .order_by(AgendaPrevistaAdmin.data)
                )
                .scalars()
                .all()
            )

    def listar_todos_periodo(
        self, data_inicio: date, data_fim: date
    ) -> Sequence[AgendaPrevistaAdmin]:
        """Lista todos os planejamentos no período."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(AgendaPrevistaAdmin)
                    .where(
                        and_(
                            AgendaPrevistaAdmin.data >= data_inicio,
                            AgendaPrevistaAdmin.data <= data_fim,
                            AgendaPrevistaAdmin.em_uso.is_(True),
                        )
                    )
                    .order_by(AgendaPrevistaAdmin.usuario_id, AgendaPrevistaAdmin.data)
                )
                .scalars()
                .all()
            )

    def criar(
        self,
        usuario_id: int,
        data: date,
        bloco_id: int | None,
        minutos_normais: int,
        minutos_extras: int,
        descricao: str | None,
        criado_por: int,
    ) -> AgendaPrevistaAdmin:
        """Cria novo planejamento."""
        with Session(self._engine) as session:
            planejamento = AgendaPrevistaAdmin(
                usuario_id=usuario_id,
                data=data,
                bloco_id=bloco_id,
                minutos_planejados_normais=minutos_normais,
                minutos_planejados_extras=minutos_extras,
                descricao=descricao,
                em_uso=True,
                criado_por=criado_por,
            )
            session.add(planejamento)
            session.commit()
            session.refresh(planejamento)
            return planejamento

    def atualizar(
        self,
        id: int,
        minutos_normais: int | None = None,
        minutos_extras: int | None = None,
        descricao: str | None = None,
    ) -> AgendaPrevistaAdmin | None:
        """Versiona planejamento existente, marcando o anterior como inativo."""
        with Session(self._engine) as session:
            planejamento = session.get(AgendaPrevistaAdmin, id)
            if not planejamento or not planejamento.em_uso:
                return None

            planejamento.em_uso = False
            novo = AgendaPrevistaAdmin(
                usuario_id=planejamento.usuario_id,
                data=planejamento.data,
                bloco_id=planejamento.bloco_id,
                minutos_planejados_normais=(
                    minutos_normais if minutos_normais is not None else planejamento.minutos_planejados_normais
                ),
                minutos_planejados_extras=(
                    minutos_extras if minutos_extras is not None else planejamento.minutos_planejados_extras
                ),
                descricao=descricao if descricao is not None else planejamento.descricao,
                em_uso=True,
                criado_por=planejamento.criado_por,
            )
            session.add(novo)
            session.commit()
            session.refresh(novo)
            return novo

    def remover(self, id: int) -> bool:
        """Inativa planejamento sem apagar histórico."""
        with Session(self._engine) as session:
            planejamento = session.get(AgendaPrevistaAdmin, id)
            if not planejamento or not planejamento.em_uso:
                return False
            planejamento.em_uso = False
            session.commit()
            return True

    def buscar_existente(
        self, usuario_id: int, data: date, bloco_id: int | None
    ) -> AgendaPrevistaAdmin | None:
        """Busca planejamento existente para usuário/data/bloco."""
        with Session(self._engine) as session:
            query = select(AgendaPrevistaAdmin).where(
                and_(
                    AgendaPrevistaAdmin.usuario_id == usuario_id,
                    AgendaPrevistaAdmin.data == data,
                    AgendaPrevistaAdmin.em_uso.is_(True),
                )
            )
            if bloco_id is not None:
                query = query.where(AgendaPrevistaAdmin.bloco_id == bloco_id)
            else:
                query = query.where(AgendaPrevistaAdmin.bloco_id.is_(None))
            return session.execute(query).scalar_one_or_none()

    def soma_minutos_planejados_dia(self, usuario_id: int, data: date) -> int:
        """Soma minutos normais planejados ativos no dia."""
        with Session(self._engine) as session:
            result = session.execute(
                select(func.coalesce(func.sum(AgendaPrevistaAdmin.minutos_planejados_normais), 0)).where(
                    and_(
                        AgendaPrevistaAdmin.usuario_id == usuario_id,
                        AgendaPrevistaAdmin.data == data,
                        AgendaPrevistaAdmin.em_uso.is_(True),
                    )
                )
            ).scalar()
            return int(result or 0)

    def remover_em_lote(self, usuario_ids: Sequence[int], datas: Sequence[date]) -> int:
        """Inativa todos os planejamentos ativos para usuários e datas informados."""
        if not usuario_ids or not datas:
            return 0
        with Session(self._engine) as session:
            planejamentos = session.execute(
                select(AgendaPrevistaAdmin).where(
                    and_(
                        AgendaPrevistaAdmin.usuario_id.in_(list(usuario_ids)),
                        AgendaPrevistaAdmin.data.in_(list(datas)),
                        AgendaPrevistaAdmin.em_uso.is_(True),
                    )
                )
            ).scalars().all()
            for item in planejamentos:
                item.em_uso = False
            session.commit()
            return len(planejamentos)
