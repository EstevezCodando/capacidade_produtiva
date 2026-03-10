"""Serviço de Agenda.

Responsável pela gestão de planejamento e lançamentos,
aplicando regras de negócio e validações.
"""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy.engine import Engine

from cp.domain.capacidade.enums import (
    CodigoAtividade,
    FaixaMinuto,
    StatusDia,
    TipoIndisponibilidade,
)
from cp.domain.capacidade.exceptions import (
    AcessoNegadoError,
    DataFuturaError,
    DiaConsolidadoError,
    DiaIndisponivelError,
    FeriadoDuplicadoError,
    IndisponibilidadeSobrepostaError,
    IntervaloInvalidoError,
    LimiteCapacidadeExcedidoError,
    RegistroNaoEncontradoError,
)
from cp.domain.capacidade.models import (
    AgendaLancamento,
    AgendaPrevistaAdmin,
    Feriado,
    IndisponibilidadeUsuario,
)
from cp.domain.capacidade.schemas import (
    ApontamentoResumo,
    DiaDaAgendaCompleto,
    PlanejamentoResponse,
)
from cp.repositories.capacidade import (
    AgendaLancamentoRepository,
    AgendaPrevistaRepository,
    CapacidadeDiaRepository,
    FeriadoRepository,
    IndisponibilidadeRepository,
    TipoAtividadeRepository,
)
from cp.services.capacidade.audit_service import AuditService
from cp.services.capacidade.capacidade_service import CapacidadeService


class AgendaService:
    """Serviço de gestão de agenda.

    Responsabilidades:
    - Gerenciar planejamento (admin)
    - Gerenciar lançamentos (operador e admin)
    - Validar regras de negócio
    - Gerenciar feriados e indisponibilidades
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._planejamento_repo = AgendaPrevistaRepository(engine)
        self._lancamento_repo = AgendaLancamentoRepository(engine)
        self._capacidade_repo = CapacidadeDiaRepository(engine)
        self._feriado_repo = FeriadoRepository(engine)
        self._indisponibilidade_repo = IndisponibilidadeRepository(engine)
        self._tipo_atividade_repo = TipoAtividadeRepository(engine)
        self._capacidade_service = CapacidadeService(engine)
        self._audit = AuditService(engine)

    # ─────────────────────────────────────────────────────────────────────────
    # Validações
    # ─────────────────────────────────────────────────────────────────────────

    def _validar_data_operador(self, data_lancamento: date, data_atual: date) -> None:
        """Valida que operador não pode lançar em data futura."""
        if data_lancamento > data_atual:
            raise DataFuturaError(data_lancamento, data_atual)

    def _validar_dia_aberto(
        self,
        usuario_id: int,
        data: date,
        faixa: FaixaMinuto,
        eh_admin: bool,
    ) -> None:
        """Valida que o dia está aberto para alterações.

        Admin pode alterar dias consolidados.
        Operador só pode alterar dias abertos.
        Em dias consolidados, apenas hora extra é permitida para operador.
        """
        capacidade = self._capacidade_repo.buscar(usuario_id, data)
        if not capacidade:
            return  # Dia não materializado ainda, OK

        if capacidade.status_dia == StatusDia.CONSOLIDADO:
            if eh_admin:
                return  # Admin pode alterar
            if faixa == FaixaMinuto.EXTRA:
                return  # Hora extra permitida em dia consolidado
            raise DiaConsolidadoError(data, permite_extra=True)

    def _validar_capacidade_normal(
        self,
        usuario_id: int,
        data: date,
        minutos_solicitados: int,
        excluir_lancamento_id: int | None = None,
    ) -> None:
        """Valida que não excede a capacidade normal do dia.

        Raises:
            LimiteCapacidadeExcedidoError: se exceder capacidade
            DiaIndisponivelError: se dia estiver indisponível
        """
        capacidade = self._capacidade_repo.buscar(usuario_id, data)

        # Se não há capacidade materializada, materializar
        if not capacidade:
            capacidade = self._capacidade_service.materializar_capacidade_dia(
                usuario_id, data, usuario_id
            )

        # Verificar se dia está indisponível
        if capacidade.eh_indisponivel:
            tipo = capacidade.tipo_indisponibilidade.value if capacidade.tipo_indisponibilidade else "indisponível"
            raise DiaIndisponivelError(data, tipo)

        # Calcular já alocado (excluindo o lançamento sendo editado)
        ja_alocado = self._lancamento_repo.soma_minutos_dia(
            usuario_id, data, FaixaMinuto.NORMAL
        )

        # Se estamos editando, descontar o valor atual
        if excluir_lancamento_id:
            lancamento_atual = self._lancamento_repo.buscar_por_id(excluir_lancamento_id)
            if lancamento_atual and lancamento_atual.faixa_minuto == FaixaMinuto.NORMAL:
                ja_alocado -= lancamento_atual.minutos

        capacidade_disponivel = capacidade.minutos_capacidade_normal_prevista - ja_alocado

        if minutos_solicitados > capacidade_disponivel:
            raise LimiteCapacidadeExcedidoError(
                capacidade_disponivel=max(0, capacidade_disponivel),
                minutos_solicitados=minutos_solicitados,
                minutos_ja_alocados=ja_alocado,
            )

    def _validar_proprietario_lancamento(
        self,
        lancamento: AgendaLancamento,
        usuario_id: int,
        eh_admin: bool,
    ) -> None:
        """Valida que o usuário pode editar o lançamento."""
        if eh_admin:
            return
        if lancamento.usuario_id != usuario_id:
            raise AcessoNegadoError(usuario_id, f"lançamento {lancamento.id}")

    # ─────────────────────────────────────────────────────────────────────────
    # Planejamento (Admin)
    # ─────────────────────────────────────────────────────────────────────────

    def criar_planejamento(
        self,
        usuario_id: int,
        data: date,
        bloco_id: int | None,
        minutos_normais: int,
        minutos_extras: int,
        descricao: str | None,
        criado_por: int,
    ) -> AgendaPrevistaAdmin:
        """Cria novo planejamento de agenda."""
        # Verificar se já existe planejamento para usuario/data/bloco
        existente = self._planejamento_repo.buscar_existente(usuario_id, data, bloco_id)
        if existente:
            # Atualizar ao invés de criar
            return self.atualizar_planejamento(
                existente.id, minutos_normais, minutos_extras, descricao, criado_por
            )

        planejamento = self._planejamento_repo.criar(
            usuario_id=usuario_id,
            data=data,
            bloco_id=bloco_id,
            minutos_normais=minutos_normais,
            minutos_extras=minutos_extras,
            descricao=descricao,
            criado_por=criado_por,
        )

        self._audit.auditar_planejamento_criado(planejamento, criado_por)
        return planejamento

    def atualizar_planejamento(
        self,
        id: int,
        minutos_normais: int | None,
        minutos_extras: int | None,
        descricao: str | None,
        atualizado_por: int,
    ) -> AgendaPrevistaAdmin:
        """Atualiza planejamento existente."""
        antes = self._planejamento_repo.buscar_por_id(id)
        if not antes:
            raise RegistroNaoEncontradoError("Planejamento", id)

        depois = self._planejamento_repo.atualizar(
            id=id,
            minutos_normais=minutos_normais,
            minutos_extras=minutos_extras,
            descricao=descricao,
        )

        self._audit.auditar_planejamento_atualizado(antes, depois, atualizado_por)
        return depois

    def remover_planejamento(self, id: int, removido_por: int) -> bool:
        """Remove planejamento."""
        planejamento = self._planejamento_repo.buscar_por_id(id)
        if not planejamento:
            raise RegistroNaoEncontradoError("Planejamento", id)

        self._audit.auditar_planejamento_removido(planejamento, removido_por)
        return self._planejamento_repo.remover(id)

    def listar_planejamento_usuario(
        self, usuario_id: int, data_inicio: date, data_fim: date
    ) -> Sequence[AgendaPrevistaAdmin]:
        """Lista planejamentos do usuário no período."""
        return self._planejamento_repo.listar_por_usuario_periodo(
            usuario_id, data_inicio, data_fim
        )

    def listar_planejamento_geral(
        self, data_inicio: date, data_fim: date
    ) -> Sequence[AgendaPrevistaAdmin]:
        """Lista todos os planejamentos no período."""
        return self._planejamento_repo.listar_todos_periodo(data_inicio, data_fim)

    # ─────────────────────────────────────────────────────────────────────────
    # Lançamentos
    # ─────────────────────────────────────────────────────────────────────────

    def criar_lancamento(
        self,
        usuario_id: int,
        data: date,
        bloco_id: int | None,
        tipo_atividade: CodigoAtividade,
        faixa: FaixaMinuto,
        minutos: int,
        descricao: str | None,
        criado_por: int,
        eh_admin: bool,
        data_atual: date,
    ) -> tuple[AgendaLancamento, list[str]]:
        """Cria novo lançamento de agenda.

        Returns:
            Tuple com o lançamento criado e lista de alertas
        """
        alertas: list[str] = []

        # Validações
        if not eh_admin:
            self._validar_data_operador(data, data_atual)

        self._validar_dia_aberto(usuario_id, data, faixa, eh_admin)

        # Validar capacidade normal
        if faixa == FaixaMinuto.NORMAL:
            self._validar_capacidade_normal(usuario_id, data, minutos)

        # Obter tipo de atividade
        tipo = self._tipo_atividade_repo.buscar_por_codigo(tipo_atividade)
        if not tipo:
            raise RegistroNaoEncontradoError("TipoAtividade", tipo_atividade.value)

        # Verificar se é dia consolidado e alertar
        capacidade = self._capacidade_repo.buscar(usuario_id, data)
        if capacidade and capacidade.status_dia == StatusDia.CONSOLIDADO:
            alertas.append("Lançamento em dia consolidado - auditoria reforçada")

        # Criar lançamento
        lancamento = self._lancamento_repo.criar(
            usuario_id=usuario_id,
            data=data,
            bloco_id=bloco_id,
            tipo_atividade_id=tipo.id,
            faixa=faixa,
            minutos=minutos,
            descricao=descricao,
            criado_por=criado_por,
        )

        self._audit.auditar_lancamento_criado(lancamento, criado_por)
        return lancamento, alertas

    def atualizar_lancamento(
        self,
        id: int,
        minutos: int | None,
        descricao: str | None,
        atualizado_por: int,
        eh_admin: bool,
    ) -> tuple[AgendaLancamento, list[str]]:
        """Atualiza lançamento existente."""
        alertas: list[str] = []

        antes = self._lancamento_repo.buscar_por_id(id)
        if not antes:
            raise RegistroNaoEncontradoError("Lançamento", id)

        # Validar propriedade
        self._validar_proprietario_lancamento(antes, atualizado_por, eh_admin)

        # Validar dia aberto
        self._validar_dia_aberto(
            antes.usuario_id, antes.data_lancamento, antes.faixa_minuto, eh_admin
        )

        # Validar capacidade se alterando minutos na faixa normal
        if minutos and antes.faixa_minuto == FaixaMinuto.NORMAL:
            self._validar_capacidade_normal(
                antes.usuario_id, antes.data_lancamento, minutos, excluir_lancamento_id=id
            )

        # Verificar dia consolidado
        capacidade = self._capacidade_repo.buscar(antes.usuario_id, antes.data_lancamento)
        if capacidade and capacidade.status_dia == StatusDia.CONSOLIDADO:
            alertas.append("Alteração em dia consolidado - auditoria reforçada")

        depois = self._lancamento_repo.atualizar(
            id=id,
            minutos=minutos,
            descricao=descricao,
            atualizado_por=atualizado_por,
        )

        self._audit.auditar_lancamento_atualizado(antes, depois, atualizado_por)
        return depois, alertas

    def remover_lancamento(
        self,
        id: int,
        removido_por: int,
        eh_admin: bool,
    ) -> bool:
        """Remove lançamento."""
        lancamento = self._lancamento_repo.buscar_por_id(id)
        if not lancamento:
            raise RegistroNaoEncontradoError("Lançamento", id)

        # Validar propriedade
        self._validar_proprietario_lancamento(lancamento, removido_por, eh_admin)

        # Validar dia aberto (admin pode remover em dia consolidado)
        self._validar_dia_aberto(
            lancamento.usuario_id,
            lancamento.data_lancamento,
            lancamento.faixa_minuto,
            eh_admin,
        )

        self._audit.auditar_lancamento_removido(lancamento, removido_por)
        return self._lancamento_repo.remover(id)

    def listar_lancamentos_usuario(
        self, usuario_id: int, data_inicio: date, data_fim: date
    ) -> Sequence[AgendaLancamento]:
        """Lista lançamentos do usuário no período."""
        return self._lancamento_repo.listar_por_usuario_periodo(
            usuario_id, data_inicio, data_fim
        )

    def buscar_lancamento(self, id: int) -> AgendaLancamento | None:
        """Busca lançamento por ID."""
        return self._lancamento_repo.buscar_por_id(id)

    # ─────────────────────────────────────────────────────────────────────────
    # Feriados
    # ─────────────────────────────────────────────────────────────────────────

    def criar_feriado(
        self, data: date, descricao: str, criado_por: int
    ) -> Feriado:
        """Cria novo feriado."""
        existente = self._feriado_repo.buscar_por_data(data)
        if existente:
            raise FeriadoDuplicadoError(data)

        feriado = self._feriado_repo.criar(data, descricao, criado_por)
        self._audit.auditar_feriado_criado(feriado, criado_por)
        return feriado

    def remover_feriado(self, id: int, removido_por: int) -> bool:
        """Remove feriado."""
        feriado = self._feriado_repo.buscar_por_id(id)
        if not feriado:
            raise RegistroNaoEncontradoError("Feriado", id)

        self._audit.auditar_feriado_removido(feriado, removido_por)
        return self._feriado_repo.remover(id)

    def listar_feriados(self) -> Sequence[Feriado]:
        """Lista todos os feriados."""
        return self._feriado_repo.listar_todos()

    def listar_feriados_periodo(
        self, data_inicio: date, data_fim: date
    ) -> Sequence[Feriado]:
        """Lista feriados no período."""
        return self._feriado_repo.listar_periodo(data_inicio, data_fim)

    # ─────────────────────────────────────────────────────────────────────────
    # Indisponibilidades
    # ─────────────────────────────────────────────────────────────────────────

    def criar_indisponibilidade(
        self,
        usuario_id: int,
        tipo: TipoIndisponibilidade,
        data_inicio: date,
        data_fim: date,
        descricao: str | None,
        criado_por: int,
    ) -> IndisponibilidadeUsuario:
        """Cria nova indisponibilidade."""
        # Validar intervalo
        if data_fim < data_inicio:
            raise IntervaloInvalidoError(data_inicio, data_fim)

        # Verificar sobreposição
        if self._indisponibilidade_repo.verificar_sobreposicao(
            usuario_id, data_inicio, data_fim
        ):
            raise IndisponibilidadeSobrepostaError(usuario_id, data_inicio, data_fim)

        # Mapear tipo para código de atividade
        mapa_tipo = {
            TipoIndisponibilidade.FERIAS: CodigoAtividade.FERIAS,
            TipoIndisponibilidade.LICENCA: CodigoAtividade.LICENCA,
            TipoIndisponibilidade.CURSO: CodigoAtividade.CURSO,
            TipoIndisponibilidade.AFASTAMENTO: CodigoAtividade.AFASTAMENTO,
        }
        codigo = mapa_tipo[tipo]

        tipo_atividade = self._tipo_atividade_repo.buscar_por_codigo(codigo)
        if not tipo_atividade:
            raise RegistroNaoEncontradoError("TipoAtividade", codigo.value)

        indisponibilidade = self._indisponibilidade_repo.criar(
            usuario_id=usuario_id,
            tipo_atividade_id=tipo_atividade.id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            descricao=descricao,
            criado_por=criado_por,
        )

        self._audit.auditar_indisponibilidade_criada(indisponibilidade, criado_por)
        return indisponibilidade

    def remover_indisponibilidade(self, id: int, removido_por: int) -> bool:
        """Remove indisponibilidade."""
        indisponibilidade = self._indisponibilidade_repo.buscar_por_id(id)
        if not indisponibilidade:
            raise RegistroNaoEncontradoError("Indisponibilidade", id)

        self._audit.auditar_indisponibilidade_removida(indisponibilidade, removido_por)
        return self._indisponibilidade_repo.remover(id)

    def listar_indisponibilidades_usuario(
        self, usuario_id: int
    ) -> Sequence[IndisponibilidadeUsuario]:
        """Lista todas as indisponibilidades do usuário."""
        return self._indisponibilidade_repo.listar_por_usuario(usuario_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Visualização Composta
    # ─────────────────────────────────────────────────────────────────────────

    def obter_agenda_completa(
        self, usuario_id: int, data_inicio: date, data_fim: date
    ) -> list[DiaDaAgendaCompleto]:
        """Obtém visão completa da agenda para o período.

        Retorna lista de dias com:
        - Status e flags do dia
        - Tetos de capacidade
        - Minutos apontados
        - Minutos ociosos
        - Planejamentos
        - Lançamentos
        """
        from datetime import timedelta

        resultado = []
        data_atual = data_inicio

        # Carregar dados em lote
        capacidades = {
            c.data: c
            for c in self._capacidade_repo.listar_periodo(usuario_id, data_inicio, data_fim)
        }
        planejamentos = self._planejamento_repo.listar_por_usuario_periodo(
            usuario_id, data_inicio, data_fim
        )
        lancamentos = self._lancamento_repo.listar_por_usuario_periodo(
            usuario_id, data_inicio, data_fim
        )

        # Agrupar por data
        planejamentos_por_data: dict[date, list[AgendaPrevistaAdmin]] = {}
        for p in planejamentos:
            planejamentos_por_data.setdefault(p.data, []).append(p)

        lancamentos_por_data: dict[date, list[AgendaLancamento]] = {}
        for l in lancamentos:
            lancamentos_por_data.setdefault(l.data_lancamento, []).append(l)

        while data_atual <= data_fim:
            capacidade = capacidades.get(data_atual)

            # Se não há capacidade materializada, criar valores padrão
            if not capacidade:
                eh_dia_util = data_atual.weekday() < 5
                eh_feriado = self._feriado_repo.eh_feriado(data_atual)
                indisponibilidade = self._indisponibilidade_repo.buscar_para_data(
                    usuario_id, data_atual
                )
                eh_indisponivel = indisponibilidade is not None

                teto_normal = 360 if (eh_dia_util and not eh_feriado and not eh_indisponivel) else 0
                teto_extra = 240
                status = StatusDia.ABERTO
                tipo_indisponibilidade = None

                if eh_indisponivel and indisponibilidade:
                    tipo = self._tipo_atividade_repo.buscar_por_id(
                        indisponibilidade.tipo_atividade_id
                    )
                    if tipo:
                        mapa = {
                            CodigoAtividade.FERIAS: TipoIndisponibilidade.FERIAS,
                            CodigoAtividade.LICENCA: TipoIndisponibilidade.LICENCA,
                            CodigoAtividade.CURSO: TipoIndisponibilidade.CURSO,
                            CodigoAtividade.AFASTAMENTO: TipoIndisponibilidade.AFASTAMENTO,
                        }
                        tipo_indisponibilidade = mapa.get(tipo.codigo)
            else:
                eh_dia_util = capacidade.eh_dia_util
                eh_feriado = capacidade.eh_feriado
                eh_indisponivel = capacidade.eh_indisponivel
                tipo_indisponibilidade = capacidade.tipo_indisponibilidade
                teto_normal = capacidade.minutos_capacidade_normal_prevista
                teto_extra = capacidade.minutos_capacidade_extra_permitida
                status = capacidade.status_dia

            # Calcular minutos apontados
            lancs_dia = lancamentos_por_data.get(data_atual, [])
            apontado_normal = sum(
                l.minutos for l in lancs_dia if l.faixa_minuto == FaixaMinuto.NORMAL
            )
            apontado_extra = sum(
                l.minutos for l in lancs_dia if l.faixa_minuto == FaixaMinuto.EXTRA
            )

            # Calcular ociosos
            minutos_ociosos = max(0, teto_normal - apontado_normal)

            # Converter planejamentos
            planejamentos_dia = planejamentos_por_data.get(data_atual, [])
            planejamentos_response = [
                PlanejamentoResponse(
                    id=p.id,
                    usuario_id=p.usuario_id,
                    data=p.data,
                    bloco_id=p.bloco_id,
                    minutos_planejados_normais=p.minutos_planejados_normais,
                    minutos_planejados_extras=p.minutos_planejados_extras,
                    descricao=p.descricao,
                    criado_por=p.criado_por,
                    criado_em=p.criado_em,
                    atualizado_em=p.atualizado_em,
                )
                for p in planejamentos_dia
            ]

            # Converter lançamentos
            lancamentos_response = []
            for l in lancs_dia:
                tipo = self._tipo_atividade_repo.buscar_por_id(l.tipo_atividade_id)
                lancamentos_response.append(
                    ApontamentoResumo(
                        id=l.id,
                        data=l.data_lancamento,
                        bloco_id=l.bloco_id,
                        bloco_nome=None,  # TODO: buscar nome do bloco
                        tipo_atividade=tipo.codigo if tipo else CodigoAtividade.BLOCO,
                        minutos=l.minutos,
                        faixa=l.faixa_minuto,
                    )
                )

            resultado.append(
                DiaDaAgendaCompleto(
                    data=data_atual,
                    status=status,
                    eh_dia_util=eh_dia_util,
                    eh_feriado=eh_feriado,
                    eh_indisponivel=eh_indisponivel,
                    tipo_indisponibilidade=tipo_indisponibilidade,
                    teto_normal_min=teto_normal,
                    teto_extra_min=teto_extra,
                    apontado_normal_min=apontado_normal,
                    apontado_extra_min=apontado_extra,
                    minutos_ociosos=minutos_ociosos,
                    planejamento=planejamentos_response,
                    lancamentos=lancamentos_response,
                )
            )

            data_atual += timedelta(days=1)

        return resultado
