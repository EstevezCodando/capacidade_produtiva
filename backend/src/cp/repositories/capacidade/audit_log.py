"""Repositório de Audit Log."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import and_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.enums import AcaoAuditoria
from cp.domain.capacidade.models import AuditLog


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
