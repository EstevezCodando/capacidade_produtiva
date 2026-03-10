"""Serviço de Auditoria.

Responsável por registrar todas as alterações no sistema
de forma centralizada e consistente.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from sqlalchemy.engine import Engine

from cp.domain.capacidade.enums import AcaoAuditoria
from cp.domain.capacidade.models import (
    AgendaLancamento,
    AgendaPrevistaAdmin,
    CapacidadeDia,
    Feriado,
    IndisponibilidadeUsuario,
    ParametroCapacidade,
)
from cp.repositories.capacidade import AuditLogRepository


class AuditService:
    """Serviço centralizado de auditoria.

    Registra todas as operações de criação, atualização e exclusão
    das entidades do módulo de capacidade.
    """

    def __init__(self, engine: Engine) -> None:
        self._repo = AuditLogRepository(engine)

    def _serializar_modelo(self, modelo: Any) -> dict[str, Any]:
        """Serializa modelo SQLAlchemy para dicionário."""
        if modelo is None:
            return {}

        resultado = {}
        for coluna in modelo.__table__.columns:
            valor = getattr(modelo, coluna.name)
            if isinstance(valor, datetime):
                resultado[coluna.name] = valor.isoformat()
            elif isinstance(valor, date):
                resultado[coluna.name] = valor.isoformat()
            elif hasattr(valor, "value"):  # Enum
                resultado[coluna.name] = valor.value
            else:
                resultado[coluna.name] = valor
        return resultado

    def registrar_criacao(
        self,
        entidade: str,
        entidade_id: int,
        modelo: Any,
        usuario_executor: int,
    ) -> None:
        """Registra criação de entidade."""
        self._repo.registrar(
            entidade=entidade,
            entidade_id=entidade_id,
            acao=AcaoAuditoria.CREATE,
            usuario_executor=usuario_executor,
            antes=None,
            depois=self._serializar_modelo(modelo),
        )

    def registrar_atualizacao(
        self,
        entidade: str,
        entidade_id: int,
        antes: Any,
        depois: Any,
        usuario_executor: int,
    ) -> None:
        """Registra atualização de entidade."""
        self._repo.registrar(
            entidade=entidade,
            entidade_id=entidade_id,
            acao=AcaoAuditoria.UPDATE,
            usuario_executor=usuario_executor,
            antes=self._serializar_modelo(antes) if antes else None,
            depois=self._serializar_modelo(depois) if depois else None,
        )

    def registrar_exclusao(
        self,
        entidade: str,
        entidade_id: int,
        modelo: Any,
        usuario_executor: int,
    ) -> None:
        """Registra exclusão de entidade."""
        self._repo.registrar(
            entidade=entidade,
            entidade_id=entidade_id,
            acao=AcaoAuditoria.DELETE,
            usuario_executor=usuario_executor,
            antes=self._serializar_modelo(modelo),
            depois=None,
        )

    def registrar_consolidacao(
        self,
        data_inicio: date,
        data_fim: date,
        usuarios_afetados: list[int],
        usuario_executor: int,
    ) -> None:
        """Registra consolidação de período."""
        self._repo.registrar(
            entidade="consolidacao_periodo",
            entidade_id=0,  # Consolidação não tem ID específico
            acao=AcaoAuditoria.CONSOLIDATE,
            usuario_executor=usuario_executor,
            antes=None,
            depois={
                "data_inicio": data_inicio.isoformat(),
                "data_fim": data_fim.isoformat(),
                "usuarios_afetados": usuarios_afetados,
            },
        )

    # Métodos específicos por entidade para melhor semântica

    def auditar_lancamento_criado(
        self, lancamento: AgendaLancamento, usuario_executor: int
    ) -> None:
        """Audita criação de lançamento."""
        self.registrar_criacao(
            entidade="agenda_lancamento",
            entidade_id=lancamento.id,
            modelo=lancamento,
            usuario_executor=usuario_executor,
        )

    def auditar_lancamento_atualizado(
        self,
        antes: AgendaLancamento,
        depois: AgendaLancamento,
        usuario_executor: int,
    ) -> None:
        """Audita atualização de lançamento."""
        self.registrar_atualizacao(
            entidade="agenda_lancamento",
            entidade_id=depois.id,
            antes=antes,
            depois=depois,
            usuario_executor=usuario_executor,
        )

    def auditar_lancamento_removido(
        self, lancamento: AgendaLancamento, usuario_executor: int
    ) -> None:
        """Audita remoção de lançamento."""
        self.registrar_exclusao(
            entidade="agenda_lancamento",
            entidade_id=lancamento.id,
            modelo=lancamento,
            usuario_executor=usuario_executor,
        )

    def auditar_planejamento_criado(
        self, planejamento: AgendaPrevistaAdmin, usuario_executor: int
    ) -> None:
        """Audita criação de planejamento."""
        self.registrar_criacao(
            entidade="agenda_prevista_admin",
            entidade_id=planejamento.id,
            modelo=planejamento,
            usuario_executor=usuario_executor,
        )

    def auditar_planejamento_atualizado(
        self,
        antes: AgendaPrevistaAdmin,
        depois: AgendaPrevistaAdmin,
        usuario_executor: int,
    ) -> None:
        """Audita atualização de planejamento."""
        self.registrar_atualizacao(
            entidade="agenda_prevista_admin",
            entidade_id=depois.id,
            antes=antes,
            depois=depois,
            usuario_executor=usuario_executor,
        )

    def auditar_planejamento_removido(
        self, planejamento: AgendaPrevistaAdmin, usuario_executor: int
    ) -> None:
        """Audita remoção de planejamento."""
        self.registrar_exclusao(
            entidade="agenda_prevista_admin",
            entidade_id=planejamento.id,
            modelo=planejamento,
            usuario_executor=usuario_executor,
        )

    def auditar_feriado_criado(
        self, feriado: Feriado, usuario_executor: int
    ) -> None:
        """Audita criação de feriado."""
        self.registrar_criacao(
            entidade="feriado",
            entidade_id=feriado.id,
            modelo=feriado,
            usuario_executor=usuario_executor,
        )

    def auditar_feriado_removido(
        self, feriado: Feriado, usuario_executor: int
    ) -> None:
        """Audita remoção de feriado."""
        self.registrar_exclusao(
            entidade="feriado",
            entidade_id=feriado.id,
            modelo=feriado,
            usuario_executor=usuario_executor,
        )

    def auditar_indisponibilidade_criada(
        self, indisponibilidade: IndisponibilidadeUsuario, usuario_executor: int
    ) -> None:
        """Audita criação de indisponibilidade."""
        self.registrar_criacao(
            entidade="indisponibilidade_usuario",
            entidade_id=indisponibilidade.id,
            modelo=indisponibilidade,
            usuario_executor=usuario_executor,
        )

    def auditar_indisponibilidade_removida(
        self, indisponibilidade: IndisponibilidadeUsuario, usuario_executor: int
    ) -> None:
        """Audita remoção de indisponibilidade."""
        self.registrar_exclusao(
            entidade="indisponibilidade_usuario",
            entidade_id=indisponibilidade.id,
            modelo=indisponibilidade,
            usuario_executor=usuario_executor,
        )

    def auditar_parametro_criado(
        self, parametro: ParametroCapacidade, usuario_executor: int
    ) -> None:
        """Audita criação de parâmetro de capacidade."""
        self.registrar_criacao(
            entidade="parametro_capacidade",
            entidade_id=parametro.id,
            modelo=parametro,
            usuario_executor=usuario_executor,
        )

    def auditar_parametro_atualizado(
        self,
        antes: ParametroCapacidade,
        depois: ParametroCapacidade,
        usuario_executor: int,
    ) -> None:
        """Audita atualização de parâmetro de capacidade."""
        self.registrar_atualizacao(
            entidade="parametro_capacidade",
            entidade_id=depois.id,
            antes=antes,
            depois=depois,
            usuario_executor=usuario_executor,
        )

    def auditar_capacidade_dia_atualizada(
        self,
        antes: CapacidadeDia | None,
        depois: CapacidadeDia,
        usuario_executor: int,
    ) -> None:
        """Audita atualização de capacidade diária."""
        if antes:
            self.registrar_atualizacao(
                entidade="capacidade_dia",
                entidade_id=depois.id,
                antes=antes,
                depois=depois,
                usuario_executor=usuario_executor,
            )
        else:
            self.registrar_criacao(
                entidade="capacidade_dia",
                entidade_id=depois.id,
                modelo=depois,
                usuario_executor=usuario_executor,
            )
