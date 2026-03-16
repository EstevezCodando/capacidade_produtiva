"""Repositório de Capacidade Diária."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import and_, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.enums import StatusDia, TipoIndisponibilidade
from cp.domain.capacidade.models import CapacidadeDia


class CapacidadeDiaRepository:
    """Repositório para capacidade diária materializada."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def buscar(self, usuario_id: int, data: date) -> CapacidadeDia | None:
        """Busca capacidade do dia para o usuário."""
        with Session(self._engine) as session:
            return session.execute(
                select(CapacidadeDia).where(
                    and_(
                        CapacidadeDia.usuario_id == usuario_id,
                        CapacidadeDia.data == data,
                    )
                )
            ).scalar_one_or_none()

    def listar_periodo(
        self, usuario_id: int, data_inicio: date, data_fim: date
    ) -> Sequence[CapacidadeDia]:
        """Lista capacidades no período para o usuário."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(CapacidadeDia)
                    .where(
                        and_(
                            CapacidadeDia.usuario_id == usuario_id,
                            CapacidadeDia.data >= data_inicio,
                            CapacidadeDia.data <= data_fim,
                        )
                    )
                    .order_by(CapacidadeDia.data)
                )
                .scalars()
                .all()
            )

    def criar_ou_atualizar(
        self,
        usuario_id: int,
        data: date,
        minutos_normal: int,
        minutos_extra: int,
        eh_dia_util: bool,
        eh_feriado: bool,
        eh_indisponivel: bool,
        tipo_indisponibilidade: TipoIndisponibilidade | None,
        status: StatusDia,
        origem_parametro: int | None,
    ) -> CapacidadeDia:
        """Cria ou atualiza capacidade do dia."""
        with Session(self._engine) as session:
            existente = session.execute(
                select(CapacidadeDia).where(
                    and_(
                        CapacidadeDia.usuario_id == usuario_id,
                        CapacidadeDia.data == data,
                    )
                )
            ).scalar_one_or_none()

            if existente:
                existente.minutos_capacidade_normal_prevista = minutos_normal
                existente.minutos_capacidade_extra_permitida = minutos_extra
                existente.eh_dia_util = eh_dia_util
                existente.eh_feriado = eh_feriado
                existente.eh_indisponivel = eh_indisponivel
                existente.tipo_indisponibilidade = tipo_indisponibilidade
                existente.status_dia = status
                existente.origem_parametro_capacidade = origem_parametro
                session.commit()
                session.refresh(existente)
                return existente

            novo = CapacidadeDia(
                usuario_id=usuario_id,
                data=data,
                minutos_capacidade_normal_prevista=minutos_normal,
                minutos_capacidade_extra_permitida=minutos_extra,
                eh_dia_util=eh_dia_util,
                eh_feriado=eh_feriado,
                eh_indisponivel=eh_indisponivel,
                tipo_indisponibilidade=tipo_indisponibilidade,
                status_dia=status,
                origem_parametro_capacidade=origem_parametro,
            )
            session.add(novo)
            session.commit()
            session.refresh(novo)
            return novo

    def consolidar_periodo(
        self, usuario_id: int, data_inicio: date, data_fim: date
    ) -> int:
        """Consolida dias no período. Retorna quantidade de dias atualizados."""
        with Session(self._engine) as session:
            result = session.execute(
                update(CapacidadeDia)
                .where(
                    and_(
                        CapacidadeDia.usuario_id == usuario_id,
                        CapacidadeDia.data >= data_inicio,
                        CapacidadeDia.data <= data_fim,
                        CapacidadeDia.status_dia == StatusDia.ABERTO,
                    )
                )
                .values(status_dia=StatusDia.CONSOLIDADO)
            )
            session.commit()
            return result.rowcount

    def listar_por_status(
        self, data_inicio: date, data_fim: date, status: StatusDia | None = None
    ) -> Sequence[CapacidadeDia]:
        """Lista capacidades no período, opcionalmente filtrado por status."""
        with Session(self._engine) as session:
            query = select(CapacidadeDia).where(
                and_(
                    CapacidadeDia.data >= data_inicio,
                    CapacidadeDia.data <= data_fim,
                )
            )
            if status:
                query = query.where(CapacidadeDia.status_dia == status)
            return session.execute(query.order_by(CapacidadeDia.data)).scalars().all()
