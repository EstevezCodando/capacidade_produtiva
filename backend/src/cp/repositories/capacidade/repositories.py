"""Repositórios do módulo de Capacidade.

Encapsula acesso a dados para agenda, lançamentos, capacidade e auditoria.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Sequence

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.enums import (
    AcaoAuditoria,
    CodigoAtividade,
    FaixaMinuto,
    StatusDia,
    TipoIndisponibilidade,
)
from cp.domain.capacidade.models import (
    AgendaLancamento,
    AgendaPrevistaAdmin,
    AuditLog,
    CapacidadeDia,
    Feriado,
    IndisponibilidadeUsuario,
    ParametroCapacidade,
    TipoAtividade,
)

# ──────────────────────────────────────────────────────────────────────────────
# Tipo de Atividade Repository
# ──────────────────────────────────────────────────────────────────────────────


class TipoAtividadeRepository:
    """Repositório para tipos de atividade."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def buscar_por_codigo(self, codigo: CodigoAtividade) -> TipoAtividade | None:
        """Busca tipo de atividade pelo código."""
        with Session(self._engine) as session:
            return session.execute(
                select(TipoAtividade).where(TipoAtividade.codigo == codigo)
            ).scalar_one_or_none()

    def listar_todos(self) -> Sequence[TipoAtividade]:
        """Lista todos os tipos de atividade."""
        with Session(self._engine) as session:
            return session.execute(select(TipoAtividade)).scalars().all()

    def buscar_por_id(self, id: int) -> TipoAtividade | None:
        """Busca tipo de atividade pelo ID."""
        with Session(self._engine) as session:
            return session.get(TipoAtividade, id)


# ──────────────────────────────────────────────────────────────────────────────
# Parâmetro de Capacidade Repository
# ──────────────────────────────────────────────────────────────────────────────


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
            query = select(ParametroCapacidade).where(
                or_(
                    # Novo período inicia dentro de um existente
                    and_(
                        ParametroCapacidade.data_inicio_vigencia <= data_inicio,
                        or_(
                            ParametroCapacidade.data_fim_vigencia.is_(None),
                            ParametroCapacidade.data_fim_vigencia >= data_inicio,
                        ),
                    ),
                    # Novo período termina dentro de um existente
                    and_(
                        data_fim.is_not(None) if data_fim else False,
                        ParametroCapacidade.data_inicio_vigencia <= data_fim,
                        or_(
                            ParametroCapacidade.data_fim_vigencia.is_(None),
                            ParametroCapacidade.data_fim_vigencia >= data_fim,
                        ),
                    ),
                    # Novo período engloba um existente
                    and_(
                        ParametroCapacidade.data_inicio_vigencia >= data_inicio,
                        or_(
                            data_fim is None,
                            ParametroCapacidade.data_fim_vigencia <= data_fim,
                        ),
                    ),
                )
            )
            if excluir_id:
                query = query.where(ParametroCapacidade.id != excluir_id)
            result = session.execute(query).scalar_one_or_none()
            return result is not None


# ──────────────────────────────────────────────────────────────────────────────
# Capacidade Dia Repository
# ──────────────────────────────────────────────────────────────────────────────


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


# ──────────────────────────────────────────────────────────────────────────────
# Agenda Prevista Repository
# ──────────────────────────────────────────────────────────────────────────────


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


# ──────────────────────────────────────────────────────────────────────────────
# Agenda Lançamento Repository
# ──────────────────────────────────────────────────────────────────────────────


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


# ──────────────────────────────────────────────────────────────────────────────
# Feriado Repository
# ──────────────────────────────────────────────────────────────────────────────


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


# ──────────────────────────────────────────────────────────────────────────────
# Indisponibilidade Repository
# ──────────────────────────────────────────────────────────────────────────────


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


# ──────────────────────────────────────────────────────────────────────────────
# Audit Log Repository
# ──────────────────────────────────────────────────────────────────────────────


class AuditLogRepository:
    """Repositório para logs de auditoria."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def registrar(
        self,
        entidade: str,
        entidade_id: int,
        acao: AcaoAuditoria,
        usuario_executor: int,
        antes: dict[str, Any] | None = None,
        depois: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Registra entrada de auditoria."""
        with Session(self._engine) as session:
            log = AuditLog(
                entidade=entidade,
                entidade_id=entidade_id,
                acao=acao,
                usuario_executor=usuario_executor,
                antes_json=antes,
                depois_json=depois,
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            return log

    def listar_por_entidade(
        self, entidade: str, entidade_id: int
    ) -> Sequence[AuditLog]:
        """Lista logs de auditoria para uma entidade específica."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(AuditLog)
                    .where(
                        and_(
                            AuditLog.entidade == entidade,
                            AuditLog.entidade_id == entidade_id,
                        )
                    )
                    .order_by(AuditLog.timestamp.desc())
                )
                .scalars()
                .all()
            )

    def listar_por_usuario(
        self, usuario_executor: int, limit: int = 100
    ) -> Sequence[AuditLog]:
        """Lista logs de auditoria por usuário executor."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(AuditLog)
                    .where(AuditLog.usuario_executor == usuario_executor)
                    .order_by(AuditLog.timestamp.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )

    def listar_periodo(
        self, data_inicio: datetime, data_fim: datetime, limit: int = 1000
    ) -> Sequence[AuditLog]:
        """Lista logs de auditoria no período."""
        with Session(self._engine) as session:
            return (
                session.execute(
                    select(AuditLog)
                    .where(
                        and_(
                            AuditLog.timestamp >= data_inicio,
                            AuditLog.timestamp <= data_fim,
                        )
                    )
                    .order_by(AuditLog.timestamp.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
