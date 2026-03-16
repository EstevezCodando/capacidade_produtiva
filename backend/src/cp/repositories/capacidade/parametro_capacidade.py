"""Repositório de Parâmetro de Capacidade."""

from __future__ import annotations

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.models import ParametroCapacidade


class ParametroCapacidadeRepository:
    """Repositório para parâmetros de capacidade."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def buscar_vigente(self, data_referencia: date) -> ParametroCapacidade | None:
        """Busca parâmetro vigente para a data de referência."""
        with Session(self._engine) as session:
            return session.execute(
                select(ParametroCapacidade)
                .where(
                    and_(
                        ParametroCapacidade.data_inicio_vigencia <= data_referencia,
                        or_(
                            ParametroCapacidade.data_fim_vigencia.is_(None),
                            ParametroCapacidade.data_fim_vigencia >= data_referencia,
                        ),
                    )
                )
                .order_by(ParametroCapacidade.data_inicio_vigencia.desc())
                .limit(1)
            ).scalar_one_or_none()

    def buscar_por_id(self, id: int) -> ParametroCapacidade | None:
        """Busca parâmetro pelo ID."""
        with Session(self._engine) as session:
            return session.get(ParametroCapacidade, id)

    def criar(
        self,
        minutos_dia_util: int,
        minutos_extra_max: int,
        data_inicio: date,
        data_fim: date | None,
        criado_por: int,
    ) -> ParametroCapacidade:
        """Cria novo parâmetro de capacidade."""
        with Session(self._engine) as session:
            param = ParametroCapacidade(
                minutos_dia_util_default=minutos_dia_util,
                minutos_extra_maximo_default=minutos_extra_max,
                data_inicio_vigencia=data_inicio,
                data_fim_vigencia=data_fim,
                criado_por=criado_por,
            )
            session.add(param)
            session.commit()
            session.refresh(param)
            return param

    def atualizar(
        self,
        id: int,
        minutos_dia_util: int | None = None,
        minutos_extra_max: int | None = None,
        data_fim: date | None = None,
    ) -> ParametroCapacidade | None:
        """Atualiza parâmetro existente."""
        with Session(self._engine) as session:
            param = session.get(ParametroCapacidade, id)
            if not param:
                return None
            if minutos_dia_util is not None:
                param.minutos_dia_util_default = minutos_dia_util
            if minutos_extra_max is not None:
                param.minutos_extra_maximo_default = minutos_extra_max
            if data_fim is not None:
                param.data_fim_vigencia = data_fim
            session.commit()
            session.refresh(param)
            return param

    def verificar_conflito_vigencia(
        self, data_inicio: date, data_fim: date | None, excluir_id: int | None = None
    ) -> bool:
        """Verifica se há conflito de vigência com parâmetros existentes."""
        with Session(self._engine) as session:
            # Novo período inicia dentro de um existente
            overlap_conditions = [
                and_(
                    ParametroCapacidade.data_inicio_vigencia <= data_inicio,
                    or_(
                        ParametroCapacidade.data_fim_vigencia.is_(None),
                        ParametroCapacidade.data_fim_vigencia >= data_inicio,
                    ),
                ),
            ]
            if data_fim is not None:
                # Novo período termina dentro de um existente
                overlap_conditions.append(
                    and_(
                        ParametroCapacidade.data_inicio_vigencia <= data_fim,
                        or_(
                            ParametroCapacidade.data_fim_vigencia.is_(None),
                            ParametroCapacidade.data_fim_vigencia >= data_fim,
                        ),
                    )
                )
                # Novo período engloba um existente (com fim definido)
                overlap_conditions.append(
                    and_(
                        ParametroCapacidade.data_inicio_vigencia >= data_inicio,
                        ParametroCapacidade.data_fim_vigencia <= data_fim,
                    )
                )
            else:
                # Novo período sem fim engloba todos que começam depois
                overlap_conditions.append(
                    ParametroCapacidade.data_inicio_vigencia >= data_inicio
                )
            query = select(ParametroCapacidade).where(or_(*overlap_conditions))
            if excluir_id:
                query = query.where(ParametroCapacidade.id != excluir_id)
            return session.execute(query).scalar_one_or_none() is not None
