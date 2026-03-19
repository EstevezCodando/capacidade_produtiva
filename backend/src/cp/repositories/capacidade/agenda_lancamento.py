"""Repositório de Agenda Lançamento (apontamentos)."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.enums import CodigoAtividade, FaixaMinuto
from cp.domain.capacidade.models import AgendaLancamento, TipoAtividade


class AgendaLancamentoRepository:
    """Repositório para lançamentos de agenda."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def buscar_por_id(self, id: int) -> AgendaLancamento | None:
        """Busca lançamento pelo ID."""
        with Session(self._engine) as session:
            return session.get(AgendaLancamento, id)

    def listar_por_usuario_periodo(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        faixa: FaixaMinuto | None = None,
    ) -> Sequence[AgendaLancamento]:
        """Lista lançamentos do usuário no período."""
        with Session(self._engine) as session:
            query = select(AgendaLancamento).where(
                and_(
                    AgendaLancamento.usuario_id == usuario_id,
                    AgendaLancamento.data_lancamento >= data_inicio,
                    AgendaLancamento.data_lancamento <= data_fim,
                    AgendaLancamento.em_uso.is_(True),
                )
            )
            if faixa:
                query = query.where(AgendaLancamento.faixa_minuto == faixa)
            return (
                session.execute(query.order_by(AgendaLancamento.data_lancamento))
                .scalars()
                .all()
            )

    def soma_minutos_dia(
        self, usuario_id: int, data: date, faixa: FaixaMinuto
    ) -> int:
        """Soma minutos lançados no dia para a faixa especificada."""
        with Session(self._engine) as session:
            result = session.execute(
                select(func.coalesce(func.sum(AgendaLancamento.minutos), 0)).where(
                    and_(
                        AgendaLancamento.usuario_id == usuario_id,
                        AgendaLancamento.data_lancamento == data,
                        AgendaLancamento.faixa_minuto == faixa,
                        AgendaLancamento.em_uso.is_(True),
                    )
                )
            ).scalar()
            return int(result or 0)

    def soma_minutos_dia_por_tipo(
        self,
        usuario_id: int,
        data: date,
        faixa: FaixaMinuto,
        tipo_codigo: CodigoAtividade,
    ) -> int:
        """Soma minutos por tipo de atividade no dia."""
        with Session(self._engine) as session:
            result = session.execute(
                select(func.coalesce(func.sum(AgendaLancamento.minutos), 0))
                .join(TipoAtividade)
                .where(
                    and_(
                        AgendaLancamento.usuario_id == usuario_id,
                        AgendaLancamento.data_lancamento == data,
                        AgendaLancamento.faixa_minuto == faixa,
                        AgendaLancamento.em_uso.is_(True),
                        TipoAtividade.codigo == tipo_codigo,
                    )
                )
            ).scalar()
            return int(result or 0)

    def criar(
        self,
        usuario_id: int,
        data: date,
        bloco_id: int | None,
        tipo_atividade_id: int,
        faixa: FaixaMinuto,
        minutos: int,
        descricao: str | None,
        criado_por: int,
    ) -> AgendaLancamento:
        """Cria novo lançamento."""
        with Session(self._engine) as session:
            lancamento = AgendaLancamento(
                usuario_id=usuario_id,
                data_lancamento=data,
                bloco_id=bloco_id,
                tipo_atividade_id=tipo_atividade_id,
                faixa_minuto=faixa,
                minutos=minutos,
                descricao=descricao,
                em_uso=True,
                consolidado=False,
                criado_por=criado_por,
            )
            session.add(lancamento)
            session.commit()
            session.refresh(lancamento)
            return lancamento

    def atualizar(
        self,
        id: int,
        minutos: int | None = None,
        descricao: str | None = None,
        atualizado_por: int | None = None,
    ) -> AgendaLancamento | None:
        """Versiona lançamento existente, preservando histórico."""
        with Session(self._engine) as session:
            lancamento = session.get(AgendaLancamento, id)
            if not lancamento or not lancamento.em_uso:
                return None

            lancamento.em_uso = False
            novo = AgendaLancamento(
                usuario_id=lancamento.usuario_id,
                data_lancamento=lancamento.data_lancamento,
                bloco_id=lancamento.bloco_id,
                tipo_atividade_id=lancamento.tipo_atividade_id,
                faixa_minuto=lancamento.faixa_minuto,
                minutos=minutos if minutos is not None else lancamento.minutos,
                descricao=descricao if descricao is not None else lancamento.descricao,
                em_uso=True,
                consolidado=False,
                criado_por=lancamento.criado_por,
                atualizado_por=atualizado_por,
            )
            session.add(novo)
            session.commit()
            session.refresh(novo)
            return novo

    def remover(self, id: int) -> bool:
        """Inativa lançamento sem apagar histórico."""
        with Session(self._engine) as session:
            lancamento = session.get(AgendaLancamento, id)
            if not lancamento or not lancamento.em_uso:
                return False
            lancamento.em_uso = False
            session.commit()
            return True

    def listar_por_dia(
        self, usuario_id: int, data: date
    ) -> Sequence[AgendaLancamento]:
        """Lista todos os lançamentos do dia."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(AgendaLancamento).where(
                        and_(
                            AgendaLancamento.usuario_id == usuario_id,
                            AgendaLancamento.data_lancamento == data,
                            AgendaLancamento.em_uso.is_(True),
                        )
                    )
                )
                .scalars()
                .all()
            )
