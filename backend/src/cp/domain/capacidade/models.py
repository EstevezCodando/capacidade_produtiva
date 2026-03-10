"""Modelos SQLAlchemy do domínio de Capacidade.

Define as tabelas do schema `capacidade` para gestão de agenda,
lançamentos, parâmetros e auditoria.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from cp.domain.capacidade.enums import (
    AcaoAuditoria,
    CodigoAtividade,
    FaixaMinuto,
    GrupoAtividade,
    StatusDia,
    TipoIndisponibilidade,
)


class Base(DeclarativeBase):
    """Classe base para modelos do módulo capacidade."""

    pass


# ──────────────────────────────────────────────────────────────────────────────
# Tipo de Atividade
# ──────────────────────────────────────────────────────────────────────────────


class TipoAtividade(Base):
    """Catálogo de tipos de atividade.

    Define os tipos disponíveis para classificação de lançamentos:
    - BLOCO: produção em bloco
    - EXTERNA: atividade externa
    - AJUSTE: ajuste administrativo
    - FERIAS, LICENCA, CURSO, AFASTAMENTO: indisponibilidades
    """

    __tablename__ = "tipo_atividade"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_tipo_atividade_codigo"),
        {"schema": "capacidade"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(
        Enum(CodigoAtividade, name="codigo_atividade", schema="capacidade"),
        nullable=False,
    )
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    grupo: Mapped[str] = mapped_column(
        Enum(GrupoAtividade, name="grupo_atividade", schema="capacidade"),
        nullable=False,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Parâmetro de Capacidade
# ──────────────────────────────────────────────────────────────────────────────


class ParametroCapacidade(Base):
    """Parâmetros globais de capacidade com vigência.

    Define os valores padrão de minutos por dia útil e máximo de hora extra.
    Suporta múltiplas vigências para histórico e planejamento.
    """

    __tablename__ = "parametro_capacidade"
    __table_args__ = (
        CheckConstraint("minutos_dia_util_default > 0", name="ck_minutos_dia_util_positivo"),
        CheckConstraint("minutos_extra_maximo_default >= 0", name="ck_minutos_extra_nao_negativo"),
        CheckConstraint(
            "data_fim_vigencia IS NULL OR data_fim_vigencia >= data_inicio_vigencia",
            name="ck_vigencia_valida",
        ),
        Index("ix_parametro_capacidade_vigencia", "data_inicio_vigencia", "data_fim_vigencia"),
        {"schema": "capacidade"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    minutos_dia_util_default: Mapped[int] = mapped_column(Integer, nullable=False, default=360)
    minutos_extra_maximo_default: Mapped[int] = mapped_column(Integer, nullable=False, default=240)
    data_inicio_vigencia: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim_vigencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    criado_por: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ──────────────────────────────────────────────────────────────────────────────
# Capacidade Diária (Materializada)
# ──────────────────────────────────────────────────────────────────────────────


class CapacidadeDia(Base):
    """Materialização da capacidade diária por usuário.

    Consolida para cada usuário e data:
    - Capacidade normal prevista (considerando parâmetros e calendário)
    - Capacidade extra permitida
    - Flags de dia útil, feriado, indisponibilidade
    - Status de consolidação
    """

    __tablename__ = "capacidade_dia"
    __table_args__ = (
        UniqueConstraint("usuario_id", "data", name="uq_capacidade_dia_usuario_data"),
        CheckConstraint("minutos_capacidade_normal_prevista >= 0", name="ck_capacidade_normal_nao_negativa"),
        CheckConstraint("minutos_capacidade_extra_permitida >= 0", name="ck_capacidade_extra_nao_negativa"),
        Index("ix_capacidade_dia_usuario_data", "usuario_id", "data"),
        Index("ix_capacidade_dia_data", "data"),
        Index("ix_capacidade_dia_status", "status_dia"),
        {"schema": "capacidade"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    minutos_capacidade_normal_prevista: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minutos_capacidade_extra_permitida: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eh_dia_util: Mapped[bool] = mapped_column(default=True, nullable=False)
    eh_feriado: Mapped[bool] = mapped_column(default=False, nullable=False)
    eh_indisponivel: Mapped[bool] = mapped_column(default=False, nullable=False)
    tipo_indisponibilidade: Mapped[str | None] = mapped_column(
        Enum(TipoIndisponibilidade, name="tipo_indisponibilidade_enum", schema="capacidade"),
        nullable=True,
    )
    status_dia: Mapped[str] = mapped_column(
        Enum(StatusDia, name="status_dia_enum", schema="capacidade"),
        nullable=False,
        default=StatusDia.ABERTO,
    )
    origem_parametro_capacidade: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("capacidade.parametro_capacidade.id"), nullable=True
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ──────────────────────────────────────────────────────────────────────────────
# Agenda Prevista (Planejamento)
# ──────────────────────────────────────────────────────────────────────────────


class AgendaPrevistaAdmin(Base):
    """Planejamento de alocação por administrador.

    Define quantos minutos cada usuário deve dedicar a cada bloco
    em determinada data, separando minutos normais e extras planejados.
    """

    __tablename__ = "agenda_prevista_admin"
    __table_args__ = (
        UniqueConstraint(
            "usuario_id", "data", "bloco_id",
            name="uq_agenda_prevista_usuario_data_bloco"
        ),
        CheckConstraint("minutos_planejados_normais >= 0", name="ck_minutos_planejados_normais_nao_negativo"),
        CheckConstraint("minutos_planejados_extras >= 0", name="ck_minutos_planejados_extras_nao_negativo"),
        Index("ix_agenda_prevista_usuario_data", "usuario_id", "data"),
        Index("ix_agenda_prevista_data", "data"),
        {"schema": "capacidade"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    bloco_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutos_planejados_normais: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minutos_planejados_extras: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_por: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ──────────────────────────────────────────────────────────────────────────────
# Agenda de Lançamentos (Realizados)
# ──────────────────────────────────────────────────────────────────────────────


class AgendaLancamento(Base):
    """Lançamentos realizados pelos operadores ou administradores.

    Registra o que de fato ocorreu: tempo dedicado a blocos,
    atividades externas, ajustes, etc. Classifica cada lançamento
    quanto à faixa (NORMAL ou EXTRA).
    """

    __tablename__ = "agenda_lancamento"
    __table_args__ = (
        CheckConstraint("minutos > 0", name="ck_minutos_positivo"),
        Index("ix_agenda_lancamento_usuario_data", "usuario_id", "data_lancamento"),
        Index("ix_agenda_lancamento_data", "data_lancamento"),
        Index("ix_agenda_lancamento_bloco", "bloco_id"),
        {"schema": "capacidade"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    data_lancamento: Mapped[date] = mapped_column(Date, nullable=False)
    bloco_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipo_atividade_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("capacidade.tipo_atividade.id"), nullable=False
    )
    faixa_minuto: Mapped[str] = mapped_column(
        Enum(FaixaMinuto, name="faixa_minuto_enum", schema="capacidade"),
        nullable=False,
    )
    minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_por: Mapped[int] = mapped_column(Integer, nullable=False)
    atualizado_por: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relacionamentos
    tipo_atividade: Mapped[TipoAtividade] = relationship("TipoAtividade", lazy="joined")


# ──────────────────────────────────────────────────────────────────────────────
# Feriados
# ──────────────────────────────────────────────────────────────────────────────


class Feriado(Base):
    """Cadastro de feriados.

    Feriados zeram a capacidade normal prevista do dia para todos os usuários.
    """

    __tablename__ = "feriado"
    __table_args__ = (
        UniqueConstraint("data", name="uq_feriado_data"),
        Index("ix_feriado_data", "data"),
        {"schema": "capacidade"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    criado_por: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ──────────────────────────────────────────────────────────────────────────────
# Indisponibilidade de Usuário
# ──────────────────────────────────────────────────────────────────────────────


class IndisponibilidadeUsuario(Base):
    """Cadastro de indisponibilidades por usuário.

    Registra períodos de férias, licenças, cursos e afastamentos.
    Zera a capacidade normal do dia para o usuário específico.
    """

    __tablename__ = "indisponibilidade_usuario"
    __table_args__ = (
        CheckConstraint("data_fim >= data_inicio", name="ck_indisponibilidade_periodo_valido"),
        Index("ix_indisponibilidade_usuario_id", "usuario_id"),
        Index("ix_indisponibilidade_periodo", "data_inicio", "data_fim"),
        {"schema": "capacidade"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_atividade_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("capacidade.tipo_atividade.id"), nullable=False
    )
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date] = mapped_column(Date, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_por: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relacionamentos
    tipo_atividade: Mapped[TipoAtividade] = relationship("TipoAtividade", lazy="joined")


# ──────────────────────────────────────────────────────────────────────────────
# Log de Auditoria
# ──────────────────────────────────────────────────────────────────────────────


class AuditLog(Base):
    """Log de auditoria para todas as alterações do módulo.

    Permite reconstruir o histórico de alterações: quem alterou,
    o que alterou, quando e o estado antes/depois.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entidade", "entidade", "entidade_id"),
        Index("ix_audit_log_timestamp", "timestamp"),
        Index("ix_audit_log_usuario", "usuario_executor"),
        {"schema": "capacidade"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entidade: Mapped[str] = mapped_column(String(100), nullable=False)
    entidade_id: Mapped[int] = mapped_column(Integer, nullable=False)
    acao: Mapped[str] = mapped_column(
        Enum(AcaoAuditoria, name="acao_auditoria_enum", schema="capacidade"),
        nullable=False,
    )
    antes_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    depois_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    usuario_executor: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
