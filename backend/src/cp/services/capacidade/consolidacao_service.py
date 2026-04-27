"""Serviço de Consolidação.

Responsável pela consolidação de períodos e verificação de pendências.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cp.domain.capacidade.enums import FaixaMinuto, StatusDia, TipoPendencia
from cp.domain.capacidade.exceptions import (
    IntervaloInvalidoError,
    PendenciaConsolidacao,
    ResultadoConsolidacao,
)
from cp.domain.capacidade.schemas import DesconsolidacaoResponse, ExportacaoInconsistenciasResponse, LinhaExportacaoCSV
from cp.repositories.capacidade import (
    AgendaLancamentoRepository,
    CapacidadeDiaRepository,
    FeriadoRepository,
    IndisponibilidadeRepository,
    TipoAtividadeRepository,
)
from cp.services.capacidade.audit_service import AuditService

if TYPE_CHECKING:
    pass


class ConsolidacaoService:
    """Serviço de consolidação de períodos.

    Responsabilidades:
    - Verificar pendências impeditivas
    - Consolidar dias (mudar status para CONSOLIDADO)
    - Gerar relatório de pendências
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._capacidade_repo = CapacidadeDiaRepository(engine)
        self._lancamento_repo = AgendaLancamentoRepository(engine)
        self._feriado_repo = FeriadoRepository(engine)
        self._indisponibilidade_repo = IndisponibilidadeRepository(engine)
        self._tipo_atividade_repo = TipoAtividadeRepository(engine)
        self._audit = AuditService(engine)

    def verificar_pendencias(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
    ) -> list[PendenciaConsolidacao]:
        """Verifica pendências para consolidação de um usuário.

        Pendências verificadas:
        - Dia útil sem nenhum lançamento
        - Soma de minutos abaixo do esperado
        - Indisponibilidade sem registro adequado
        """
        if data_fim < data_inicio:
            raise IntervaloInvalidoError(data_inicio, data_fim)

        pendencias: list[PendenciaConsolidacao] = []
        data_atual = data_inicio

        while data_atual <= data_fim:
            capacidade = self._capacidade_repo.buscar(usuario_id, data_atual)

            # Se não há capacidade materializada, considerar dia como não tratado
            if not capacidade:
                # Verificar se deveria ter capacidade
                eh_dia_util = data_atual.weekday() < 5
                eh_feriado = self._feriado_repo.eh_feriado(data_atual)
                indisponibilidade = self._indisponibilidade_repo.buscar_para_data(
                    usuario_id, data_atual
                )

                if eh_dia_util and not eh_feriado and not indisponibilidade:
                    pendencias.append(
                        PendenciaConsolidacao(
                            usuario_id=usuario_id,
                            data=data_atual,
                            tipo=TipoPendencia.SEM_LANCAMENTO,
                            motivo="Dia útil sem capacidade materializada nem lançamentos",
                        )
                    )
                data_atual += timedelta(days=1)
                continue

            # Pular dias já consolidados
            if capacidade.status_dia == StatusDia.CONSOLIDADO:
                data_atual += timedelta(days=1)
                continue

            # Verificar dias indisponíveis
            if capacidade.eh_indisponivel:
                # Verificar se há indisponibilidade cadastrada
                indisponibilidade = self._indisponibilidade_repo.buscar_para_data(
                    usuario_id, data_atual
                )
                if not indisponibilidade:
                    pendencias.append(
                        PendenciaConsolidacao(
                            usuario_id=usuario_id,
                            data=data_atual,
                            tipo=TipoPendencia.INDISPONIBILIDADE_NAO_TRATADA,
                            motivo="Dia marcado como indisponível mas sem cadastro de indisponibilidade",
                        )
                    )
                data_atual += timedelta(days=1)
                continue

            # Verificar dias úteis sem feriado
            if capacidade.eh_dia_util and not capacidade.eh_feriado:
                # Verificar se há lançamentos
                lancamentos = self._lancamento_repo.listar_por_dia(usuario_id, data_atual)

                if not lancamentos:
                    pendencias.append(
                        PendenciaConsolidacao(
                            usuario_id=usuario_id,
                            data=data_atual,
                            tipo=TipoPendencia.SEM_LANCAMENTO,
                            motivo="Dia útil sem nenhum lançamento",
                            minutos_nao_lancados=capacidade.minutos_capacidade_normal_prevista,
                        )
                    )
                else:
                    # Verificar soma de minutos normais
                    soma_normal = sum(
                        lanc.minutos
                        for lanc in lancamentos
                        if lanc.faixa_minuto == FaixaMinuto.NORMAL
                    )

                    # Se a soma é muito baixa (menos de 50% do esperado), alertar
                    limite_minimo = capacidade.minutos_capacidade_normal_prevista * 0.5
                    if soma_normal < limite_minimo:
                        faltam = max(0, capacidade.minutos_capacidade_normal_prevista - soma_normal)
                        pendencias.append(
                            PendenciaConsolidacao(
                                usuario_id=usuario_id,
                                data=data_atual,
                                tipo=TipoPendencia.LANCAMENTO_INCOMPLETO,
                                motivo=(
                                    f"Soma de minutos normais ({soma_normal}) abaixo de 50% "
                                    f"do esperado ({capacidade.minutos_capacidade_normal_prevista})"
                                ),
                                minutos_nao_lancados=faltam,
                            )
                        )

            data_atual += timedelta(days=1)

        return pendencias

    def verificar_pendencias_todos_usuarios(
        self,
        usuarios_ids: list[int],
        data_inicio: date,
        data_fim: date,
    ) -> list[PendenciaConsolidacao]:
        """Verifica pendências para múltiplos usuários."""
        todas_pendencias: list[PendenciaConsolidacao] = []

        for usuario_id in usuarios_ids:
            pendencias = self.verificar_pendencias(usuario_id, data_inicio, data_fim)
            todas_pendencias.extend(pendencias)

        return todas_pendencias

    def consolidar_periodo(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        executor_id: int,
        ignorar_pendencias: bool = False,
    ) -> ResultadoConsolidacao:
        """Consolida período para o usuário.

        Se ignorar_pendencias=False e houver pendências, não consolida.
        Se ignorar_pendencias=True, consolida mesmo com pendências (apenas admin).

        Returns:
            ResultadoConsolidacao com status e lista de pendências
        """
        if data_fim < data_inicio:
            raise IntervaloInvalidoError(data_inicio, data_fim)

        # Verificar pendências
        pendencias = self.verificar_pendencias(usuario_id, data_inicio, data_fim)

        if pendencias and not ignorar_pendencias:
            return ResultadoConsolidacao(
                consolidado=False,
                pendencias=pendencias,
                mensagem=f"Encontradas {len(pendencias)} pendências. Resolva antes de consolidar.",
            )

        # Consolidar dias
        dias_consolidados = self._capacidade_repo.consolidar_periodo(
            usuario_id, data_inicio, data_fim
        )

        # Auditar
        self._audit.registrar_consolidacao(
            data_inicio=data_inicio,
            data_fim=data_fim,
            usuarios_afetados=[usuario_id],
            usuario_executor=executor_id,
        )

        mensagem = f"Consolidados {dias_consolidados} dias."
        if pendencias:
            mensagem += f" (Ignoradas {len(pendencias)} pendências)"

        return ResultadoConsolidacao(
            consolidado=True,
            pendencias=pendencias,
            mensagem=mensagem,
        )

    def consolidar_periodo_todos_usuarios(
        self,
        usuarios_ids: list[int],
        data_inicio: date,
        data_fim: date,
        executor_id: int,
        ignorar_pendencias: bool = False,
    ) -> ResultadoConsolidacao:
        """Consolida período para múltiplos usuários.

        Se qualquer usuário tiver pendência e ignorar_pendencias=False,
        nenhum usuário é consolidado.
        """
        if data_fim < data_inicio:
            raise IntervaloInvalidoError(data_inicio, data_fim)

        # Verificar todas as pendências primeiro
        todas_pendencias = self.verificar_pendencias_todos_usuarios(
            usuarios_ids, data_inicio, data_fim
        )

        if todas_pendencias and not ignorar_pendencias:
            return ResultadoConsolidacao(
                consolidado=False,
                pendencias=todas_pendencias,
                mensagem=f"Encontradas {len(todas_pendencias)} pendências em {len(set(p.usuario_id for p in todas_pendencias))} usuários.",
            )

        # Consolidar todos
        total_dias = 0
        for usuario_id in usuarios_ids:
            dias = self._capacidade_repo.consolidar_periodo(
                usuario_id, data_inicio, data_fim
            )
            total_dias += dias
            # Sincronizar flag consolidado nos lançamentos do período
            self._lancamento_repo.marcar_consolidado_periodo(
                usuario_id, data_inicio, data_fim, consolidado=True
            )

        # Auditar
        self._audit.registrar_consolidacao(
            data_inicio=data_inicio,
            data_fim=data_fim,
            usuarios_afetados=usuarios_ids,
            usuario_executor=executor_id,
        )

        mensagem = f"Consolidados {total_dias} dias para {len(usuarios_ids)} usuários."
        if todas_pendencias:
            mensagem += f" (Ignoradas {len(todas_pendencias)} pendências)"

        return ResultadoConsolidacao(
            consolidado=True,
            pendencias=todas_pendencias,
            mensagem=mensagem,
        )

    def desconsolidar_periodo(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        executor_id: int,
    ) -> DesconsolidacaoResponse:
        """Reabre período consolidado para o usuário."""
        if data_fim < data_inicio:
            raise IntervaloInvalidoError(data_inicio, data_fim)

        dias = self._capacidade_repo.desconsolidar_periodo(usuario_id, data_inicio, data_fim)

        self._audit.registrar_desconsolidacao(
            data_inicio=data_inicio,
            data_fim=data_fim,
            usuarios_afetados=[usuario_id],
            usuario_executor=executor_id,
        )

        return DesconsolidacaoResponse(
            desconsolidado=True,
            dias_reabertos=dias,
            mensagem=f"Reabertos {dias} dias para edição.",
        )

    def desconsolidar_periodo_todos_usuarios(
        self,
        usuarios_ids: list[int],
        data_inicio: date,
        data_fim: date,
        executor_id: int,
    ) -> DesconsolidacaoResponse:
        """Reabre período consolidado para múltiplos usuários."""
        if data_fim < data_inicio:
            raise IntervaloInvalidoError(data_inicio, data_fim)

        total_dias = 0
        for usuario_id in usuarios_ids:
            total_dias += self._capacidade_repo.desconsolidar_periodo(
                usuario_id, data_inicio, data_fim
            )
            # Reverter flag consolidado nos lançamentos do período
            self._lancamento_repo.marcar_consolidado_periodo(
                usuario_id, data_inicio, data_fim, consolidado=False
            )

        self._audit.registrar_desconsolidacao(
            data_inicio=data_inicio,
            data_fim=data_fim,
            usuarios_afetados=usuarios_ids,
            usuario_executor=executor_id,
        )

        return DesconsolidacaoResponse(
            desconsolidado=True,
            dias_reabertos=total_dias,
            mensagem=f"Reabertos {total_dias} dias para {len(usuarios_ids)} usuário(s).",
        )

    def obter_inconsistencias(
        self,
        usuarios_ids: list[int],
        data_inicio: date,
        data_fim: date,
    ) -> ExportacaoInconsistenciasResponse:
        """Retorna dias sem lançamento (ou incompletos) para exportação CSV.

        Inclui apenas pendências do tipo SEM_LANCAMENTO e LANCAMENTO_INCOMPLETO.
        Enriquece com nome do usuário via JOIN ao dgeo.usuarios.
        """
        from sqlalchemy import text

        usuarios_nomes: dict[int, str] = {}
        with Session(self._engine) as session:
            rows = session.execute(
                text("SELECT id, COALESCE(nome_guerra, nome) AS nome FROM dgeo.usuarios WHERE id = ANY(:ids)"),
                {"ids": list(usuarios_ids)},
            ).fetchall()
            for row in rows:
                usuarios_nomes[row.id] = row.nome

        pendencias_totais = self.verificar_pendencias_todos_usuarios(
            usuarios_ids, data_inicio, data_fim
        )

        linhas: list[LinhaExportacaoCSV] = []
        for p in pendencias_totais:
            if p.tipo in (TipoPendencia.SEM_LANCAMENTO, TipoPendencia.LANCAMENTO_INCOMPLETO):
                linhas.append(
                    LinhaExportacaoCSV(
                        nome_usuario=usuarios_nomes.get(p.usuario_id, f"Usuário {p.usuario_id}"),
                        data=p.data,
                        minutos_nao_lancados=p.minutos_nao_lancados or 0,
                    )
                )

        # Ordenar por nome e depois data
        linhas.sort(key=lambda x: (x.nome_usuario, x.data))

        usuarios_com_pendencia = {ln.nome_usuario for ln in linhas}

        return ExportacaoInconsistenciasResponse(
            linhas=linhas,
            total_usuarios=len(usuarios_com_pendencia),
            total_dias=len(linhas),
        )

    def obter_status_dias(
        self, data_inicio: date, data_fim: date
    ) -> list[dict[str, date | str | int]]:
        """Obtém status de todos os dias no período."""
        capacidades = self._capacidade_repo.listar_por_status(data_inicio, data_fim)

        resultado = []
        for cap in capacidades:
            resultado.append(
                {
                    "data": cap.data,
                    "status": cap.status_dia.value,
                    "usuario_id": cap.usuario_id,
                }
            )

        return resultado
