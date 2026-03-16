"""Serviço de Capacidade.

Responsável pela gestão de parâmetros de capacidade,
materialização de capacidade diária e cálculos analíticos.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence

from sqlalchemy.engine import Engine

from cp.domain.capacidade.constants import (
    DIAS_UTEIS_SEMANA,
    MINUTOS_DIA_UTIL_DEFAULT,
    MINUTOS_EXTRA_MAXIMO_DEFAULT,
)
from cp.domain.capacidade.enums import (
    CodigoAtividade,
    FaixaMinuto,
    StatusDia,
    TipoIndisponibilidade,
)
from cp.domain.capacidade.exceptions import (
    RegistroNaoEncontradoError,
    VigenciaConflitanteError,
)
from cp.domain.capacidade.models import CapacidadeDia, ParametroCapacidade
from cp.domain.capacidade.schemas import ResumoCapacidadePeriodo
from cp.repositories.capacidade import (
    AgendaLancamentoRepository,
    AgendaPrevistaRepository,
    CapacidadeDiaRepository,
    FeriadoRepository,
    IndisponibilidadeRepository,
    ParametroCapacidadeRepository,
    TipoAtividadeRepository,
)
from cp.services.capacidade.audit_service import AuditService


class CapacidadeService:
    """Serviço de gestão de capacidade.

    Responsabilidades:
    - Gerenciar parâmetros de capacidade
    - Materializar capacidade diária
    - Calcular métricas analíticas
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._param_repo = ParametroCapacidadeRepository(engine)
        self._capacidade_repo = CapacidadeDiaRepository(engine)
        self._feriado_repo = FeriadoRepository(engine)
        self._indisponibilidade_repo = IndisponibilidadeRepository(engine)
        self._lancamento_repo = AgendaLancamentoRepository(engine)
        self._planejamento_repo = AgendaPrevistaRepository(engine)
        self._tipo_atividade_repo = TipoAtividadeRepository(engine)
        self._audit = AuditService(engine)

    # ─────────────────────────────────────────────────────────────────────────
    # Parâmetros de Capacidade
    # ─────────────────────────────────────────────────────────────────────────

    def obter_parametro_vigente(self, data_referencia: date) -> ParametroCapacidade | None:
        """Obtém parâmetro de capacidade vigente para a data."""
        return self._param_repo.buscar_vigente(data_referencia)

    def criar_parametro(
        self,
        minutos_dia_util: int,
        minutos_extra_max: int,
        data_inicio: date,
        data_fim: date | None,
        criado_por: int,
    ) -> ParametroCapacidade:
        """Cria novo parâmetro de capacidade.

        Raises:
            VigenciaConflitanteError: se houver conflito de vigência
        """
        if self._param_repo.verificar_conflito_vigencia(data_inicio, data_fim):
            raise VigenciaConflitanteError(data_inicio, data_fim)

        parametro = self._param_repo.criar(
            minutos_dia_util=minutos_dia_util,
            minutos_extra_max=minutos_extra_max,
            data_inicio=data_inicio,
            data_fim=data_fim,
            criado_por=criado_por,
        )

        self._audit.auditar_parametro_criado(parametro, criado_por)
        return parametro

    def atualizar_parametro(
        self,
        id: int,
        minutos_dia_util: int | None,
        minutos_extra_max: int | None,
        data_fim: date | None,
        atualizado_por: int,
    ) -> ParametroCapacidade:
        """Atualiza parâmetro existente.

        Raises:
            RegistroNaoEncontradoError: se parâmetro não existir
        """
        antes = self._param_repo.buscar_por_id(id)
        if not antes:
            raise RegistroNaoEncontradoError("ParametroCapacidade", id)

        depois = self._param_repo.atualizar(
            id=id,
            minutos_dia_util=minutos_dia_util,
            minutos_extra_max=minutos_extra_max,
            data_fim=data_fim,
        )

        if depois is None:
            raise RegistroNaoEncontradoError("ParametroCapacidade", id)
        self._audit.auditar_parametro_atualizado(antes, depois, atualizado_por)
        return depois

    # ─────────────────────────────────────────────────────────────────────────
    # Capacidade Diária
    # ─────────────────────────────────────────────────────────────────────────

    def _eh_dia_util(self, data: date) -> bool:
        """Verifica se é dia útil (não é fim de semana)."""
        return data.weekday() in DIAS_UTEIS_SEMANA

    def _obter_tipo_indisponibilidade(
        self, codigo: CodigoAtividade
    ) -> TipoIndisponibilidade | None:
        """Converte código de atividade para tipo de indisponibilidade."""
        mapa = {
            CodigoAtividade.FERIAS: TipoIndisponibilidade.FERIAS,
            CodigoAtividade.LICENCA: TipoIndisponibilidade.LICENCA,
            CodigoAtividade.CURSO: TipoIndisponibilidade.CURSO,
            CodigoAtividade.AFASTAMENTO: TipoIndisponibilidade.AFASTAMENTO,
        }
        return mapa.get(codigo)

    def materializar_capacidade_dia(
        self,
        usuario_id: int,
        data: date,
        executor_id: int,
    ) -> CapacidadeDia:
        """Materializa a capacidade de um dia específico para o usuário.

        Considera:
        - Parâmetros de capacidade vigentes
        - Calendário (fim de semana)
        - Feriados
        - Indisponibilidades do usuário
        """
        # Buscar estado anterior para auditoria
        antes = self._capacidade_repo.buscar(usuario_id, data)

        # Obter parâmetro vigente
        parametro = self._param_repo.buscar_vigente(data)
        minutos_normal = parametro.minutos_dia_util_default if parametro else MINUTOS_DIA_UTIL_DEFAULT
        minutos_extra = parametro.minutos_extra_maximo_default if parametro else MINUTOS_EXTRA_MAXIMO_DEFAULT
        origem_param = parametro.id if parametro else None

        # Verificar se é dia útil
        eh_dia_util = self._eh_dia_util(data)

        # Verificar feriado
        eh_feriado = self._feriado_repo.eh_feriado(data)

        # Verificar indisponibilidade
        indisponibilidade = self._indisponibilidade_repo.buscar_para_data(usuario_id, data)
        eh_indisponivel = indisponibilidade is not None
        tipo_indisponibilidade = None

        if eh_indisponivel and indisponibilidade:
            tipo = self._tipo_atividade_repo.buscar_por_id(
                indisponibilidade.tipo_atividade_id
            )
            if tipo:
                tipo_indisponibilidade = self._obter_tipo_indisponibilidade(tipo.codigo)

        # Calcular capacidade normal prevista
        # Zera se: não é dia útil, é feriado, ou está indisponível
        if not eh_dia_util or eh_feriado or eh_indisponivel:
            minutos_capacidade_normal = 0
        else:
            minutos_capacidade_normal = minutos_normal

        # Manter status existente se já estiver consolidado
        status = StatusDia.ABERTO
        if antes and antes.status_dia == StatusDia.CONSOLIDADO:
            status = StatusDia.CONSOLIDADO

        # Criar ou atualizar
        depois = self._capacidade_repo.criar_ou_atualizar(
            usuario_id=usuario_id,
            data=data,
            minutos_normal=minutos_capacidade_normal,
            minutos_extra=minutos_extra,
            eh_dia_util=eh_dia_util,
            eh_feriado=eh_feriado,
            eh_indisponivel=eh_indisponivel,
            tipo_indisponibilidade=tipo_indisponibilidade,
            status=status,
            origem_parametro=origem_param,
        )

        # Auditar se houve mudança
        if antes:
            self._audit.auditar_capacidade_dia_atualizada(antes, depois, executor_id)
        else:
            self._audit.auditar_capacidade_dia_atualizada(None, depois, executor_id)

        return depois

    def materializar_periodo(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        executor_id: int,
    ) -> list[CapacidadeDia]:
        """Materializa capacidade para um período inteiro."""
        resultado = []
        data_atual = data_inicio

        while data_atual <= data_fim:
            cap = self.materializar_capacidade_dia(usuario_id, data_atual, executor_id)
            resultado.append(cap)
            data_atual += timedelta(days=1)

        return resultado

    def obter_capacidade_dia(self, usuario_id: int, data: date) -> CapacidadeDia | None:
        """Obtém capacidade materializada do dia."""
        return self._capacidade_repo.buscar(usuario_id, data)

    def listar_capacidade_periodo(
        self, usuario_id: int, data_inicio: date, data_fim: date
    ) -> Sequence[CapacidadeDia]:
        """Lista capacidades do período."""
        return self._capacidade_repo.listar_periodo(usuario_id, data_inicio, data_fim)

    # ─────────────────────────────────────────────────────────────────────────
    # Cálculos Analíticos
    # ─────────────────────────────────────────────────────────────────────────

    def calcular_resumo_periodo(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        bloco_id: int | None = None,
    ) -> ResumoCapacidadePeriodo:
        """Calcula resumo analítico de capacidade para o período.

        Retorna:
        - minutos_previstos_normais: capacidade normal prevista no período
        - minutos_realizados_bloco_normais: minutos em bloco (faixa normal)
        - minutos_perdidos_externas_normais: minutos em externa (faixa normal)
        - minutos_nao_alocados: dias de indisponibilidade
        - minutos_ociosos: previsto - realizado
        - minutos_extras_*: hora extra por categoria
        """
        # Obter capacidades do período
        capacidades = self._capacidade_repo.listar_periodo(usuario_id, data_inicio, data_fim)

        # Inicializar contadores
        minutos_previstos_normais = 0
        minutos_nao_alocados = 0

        for cap in capacidades:
            if cap.eh_indisponivel:
                # Dias indisponíveis: contar como não alocado
                # Usar o parâmetro vigente para saber quanto seria
                param = self._param_repo.buscar_vigente(cap.data)
                if param and cap.eh_dia_util and not cap.eh_feriado:
                    minutos_nao_alocados += param.minutos_dia_util_default
            else:
                minutos_previstos_normais += cap.minutos_capacidade_normal_prevista

        # Calcular minutos realizados por tipo
        lancamentos = self._lancamento_repo.listar_por_usuario_periodo(
            usuario_id, data_inicio, data_fim
        )

        minutos_bloco_normal = 0
        minutos_externa_normal = 0
        minutos_ajuste_normal = 0
        minutos_bloco_extra = 0
        minutos_externa_extra = 0
        minutos_ajuste_extra = 0

        for lanc in lancamentos:
            # Filtrar por bloco se especificado
            if bloco_id is not None and lanc.bloco_id != bloco_id:
                continue

            tipo = self._tipo_atividade_repo.buscar_por_id(lanc.tipo_atividade_id)
            if not tipo:
                continue

            if lanc.faixa_minuto == FaixaMinuto.NORMAL:
                if tipo.codigo == CodigoAtividade.BLOCO:
                    minutos_bloco_normal += lanc.minutos
                elif tipo.codigo == CodigoAtividade.EXTERNA:
                    minutos_externa_normal += lanc.minutos
                elif tipo.codigo == CodigoAtividade.AJUSTE:
                    minutos_ajuste_normal += lanc.minutos
            else:  # EXTRA
                if tipo.codigo == CodigoAtividade.BLOCO:
                    minutos_bloco_extra += lanc.minutos
                elif tipo.codigo == CodigoAtividade.EXTERNA:
                    minutos_externa_extra += lanc.minutos
                elif tipo.codigo == CodigoAtividade.AJUSTE:
                    minutos_ajuste_extra += lanc.minutos

        # Calcular ociosos (apenas faixa normal)
        minutos_realizados_normal = minutos_bloco_normal + minutos_externa_normal + minutos_ajuste_normal
        minutos_ociosos = max(0, minutos_previstos_normais - minutos_realizados_normal)

        return ResumoCapacidadePeriodo(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            bloco_id=bloco_id,
            minutos_previstos_normais=minutos_previstos_normais,
            minutos_realizados_bloco_normais=minutos_bloco_normal,
            minutos_perdidos_externas_normais=minutos_externa_normal,
            minutos_nao_alocados=minutos_nao_alocados,
            minutos_ociosos=minutos_ociosos,
            minutos_extras_bloco=minutos_bloco_extra,
            minutos_extras_externas=minutos_externa_extra,
            minutos_extras_totais=minutos_bloco_extra + minutos_externa_extra + minutos_ajuste_extra,
        )

    def calcular_minutos_disponiveis_dia(
        self, usuario_id: int, data: date, faixa: FaixaMinuto
    ) -> int:
        """Calcula minutos ainda disponíveis para lançamento no dia.

        Para faixa NORMAL: capacidade_prevista - já_alocado
        Para faixa EXTRA: limite_extra - já_alocado_extra
        """
        capacidade = self._capacidade_repo.buscar(usuario_id, data)
        if not capacidade:
            return 0

        ja_alocado = self._lancamento_repo.soma_minutos_dia(usuario_id, data, faixa)

        if faixa == FaixaMinuto.NORMAL:
            return max(0, capacidade.minutos_capacidade_normal_prevista - ja_alocado)
        else:
            return max(0, capacidade.minutos_capacidade_extra_permitida - ja_alocado)
