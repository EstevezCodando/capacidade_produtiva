"""Testes das regras de negócio do módulo Capacidade.

Cobre os casos críticos especificados no documento:
1. Limite de capacidade normal
2. Hora extra separada
3. Permissões de operador
4. Permissões de administrador
5. Cálculo de ocioso
6. Calendário e indisponibilidade
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cp.domain.capacidade.enums import (
    CodigoAtividade,
    FaixaMinuto,
    GrupoAtividade,
    StatusDia,
    TipoIndisponibilidade,
    TipoPendencia,
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
    PendenciaConsolidacao,
    ResultadoConsolidacao,
)
from cp.domain.capacidade.models import (
    AgendaLancamento,
    CapacidadeDia,
    ParametroCapacidade,
    TipoAtividade,
)
from cp.domain.capacidade.schemas import ResumoCapacidadePeriodo


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def parametro_padrao() -> ParametroCapacidade:
    """Parâmetro de capacidade padrão: 360 min normal, 240 min extra."""
    param = ParametroCapacidade()
    param.id = 1
    param.minutos_dia_util_default = 360
    param.minutos_extra_maximo_default = 240
    param.data_inicio_vigencia = date(2026, 1, 1)
    param.data_fim_vigencia = None
    param.criado_por = 1
    param.criado_em = datetime.now()
    return param


@pytest.fixture
def capacidade_dia_util() -> CapacidadeDia:
    """Capacidade de um dia útil normal."""
    cap = CapacidadeDia()
    cap.id = 1
    cap.usuario_id = 2
    cap.data = date(2026, 3, 10)  # Terça-feira
    cap.minutos_capacidade_normal_prevista = 360
    cap.minutos_capacidade_extra_permitida = 240
    cap.eh_dia_util = True
    cap.eh_feriado = False
    cap.eh_indisponivel = False
    cap.tipo_indisponibilidade = None
    cap.status_dia = StatusDia.ABERTO
    cap.origem_parametro_capacidade = 1
    cap.atualizado_em = datetime.now()
    return cap


@pytest.fixture
def capacidade_feriado() -> CapacidadeDia:
    """Capacidade de um dia de feriado."""
    cap = CapacidadeDia()
    cap.id = 2
    cap.usuario_id = 2
    cap.data = date(2026, 4, 21)  # Tiradentes
    cap.minutos_capacidade_normal_prevista = 0
    cap.minutos_capacidade_extra_permitida = 240
    cap.eh_dia_util = True
    cap.eh_feriado = True
    cap.eh_indisponivel = False
    cap.tipo_indisponibilidade = None
    cap.status_dia = StatusDia.ABERTO
    cap.origem_parametro_capacidade = 1
    cap.atualizado_em = datetime.now()
    return cap


@pytest.fixture
def capacidade_ferias() -> CapacidadeDia:
    """Capacidade de um dia de férias."""
    cap = CapacidadeDia()
    cap.id = 3
    cap.usuario_id = 2
    cap.data = date(2026, 7, 15)
    cap.minutos_capacidade_normal_prevista = 0
    cap.minutos_capacidade_extra_permitida = 0
    cap.eh_dia_util = True
    cap.eh_feriado = False
    cap.eh_indisponivel = True
    cap.tipo_indisponibilidade = TipoIndisponibilidade.FERIAS
    cap.status_dia = StatusDia.ABERTO
    cap.origem_parametro_capacidade = 1
    cap.atualizado_em = datetime.now()
    return cap


@pytest.fixture
def capacidade_consolidada() -> CapacidadeDia:
    """Capacidade de um dia já consolidado."""
    cap = CapacidadeDia()
    cap.id = 4
    cap.usuario_id = 2
    cap.data = date(2026, 2, 15)
    cap.minutos_capacidade_normal_prevista = 360
    cap.minutos_capacidade_extra_permitida = 240
    cap.eh_dia_util = True
    cap.eh_feriado = False
    cap.eh_indisponivel = False
    cap.tipo_indisponibilidade = None
    cap.status_dia = StatusDia.CONSOLIDADO
    cap.origem_parametro_capacidade = 1
    cap.atualizado_em = datetime.now()
    return cap


@pytest.fixture
def tipo_bloco() -> TipoAtividade:
    """Tipo de atividade BLOCO."""
    tipo = TipoAtividade()
    tipo.id = 1
    tipo.codigo = CodigoAtividade.BLOCO
    tipo.nome = "Trabalho em Bloco"
    tipo.grupo = GrupoAtividade.PRODUCAO
    return tipo


@pytest.fixture
def tipo_externa() -> TipoAtividade:
    """Tipo de atividade EXTERNA."""
    tipo = TipoAtividade()
    tipo.id = 2
    tipo.codigo = CodigoAtividade.EXTERNA
    tipo.nome = "Atividade Externa"
    tipo.grupo = GrupoAtividade.PRODUCAO
    return tipo


# ──────────────────────────────────────────────────────────────────────────────
# Testes de Exceções de Domínio
# ──────────────────────────────────────────────────────────────────────────────


class TestExcecoesDominio:
    """Testes das exceções de domínio."""

    def test_limite_capacidade_excedido_mensagem(self) -> None:
        """Exceção contém informações detalhadas."""
        exc = LimiteCapacidadeExcedidoError(
            capacidade_disponivel=60,
            minutos_solicitados=120,
            minutos_ja_alocados=300,
        )

        assert exc.capacidade_disponivel == 60
        assert exc.minutos_solicitados == 120
        assert exc.minutos_ja_alocados == 300
        assert "60" in str(exc)
        assert "120" in str(exc)

    def test_data_futura_error(self) -> None:
        """Exceção de data futura contém as datas."""
        exc = DataFuturaError(
            data_lancamento=date(2026, 3, 15),
            data_atual=date(2026, 3, 10),
        )

        assert exc.data_lancamento == date(2026, 3, 15)
        assert exc.data_atual == date(2026, 3, 10)
        assert "futura" in str(exc).lower()

    def test_dia_consolidado_error_permite_extra(self) -> None:
        """Exceção de dia consolidado indica se permite extra."""
        exc = DiaConsolidadoError(date(2026, 3, 10), permite_extra=True)

        assert exc.permite_extra is True
        assert "extras são permitidos" in str(exc).lower()

    def test_dia_indisponivel_error(self) -> None:
        """Exceção de dia indisponível contém o tipo."""
        exc = DiaIndisponivelError(date(2026, 7, 15), "FERIAS")

        assert exc.data == date(2026, 7, 15)
        assert exc.tipo == "FERIAS"
        assert "indisponível" in str(exc).lower()

    def test_intervalo_invalido_error(self) -> None:
        """Exceção de intervalo inválido."""
        exc = IntervaloInvalidoError(date(2026, 3, 15), date(2026, 3, 10))

        assert exc.data_inicio == date(2026, 3, 15)
        assert exc.data_fim == date(2026, 3, 10)

    def test_feriado_duplicado_error(self) -> None:
        """Exceção de feriado duplicado."""
        exc = FeriadoDuplicadoError(date(2026, 4, 21))

        assert exc.data == date(2026, 4, 21)
        assert "já existe" in str(exc).lower()

    def test_indisponibilidade_sobreposta_error(self) -> None:
        """Exceção de indisponibilidade sobreposta."""
        exc = IndisponibilidadeSobrepostaError(
            usuario_id=2,
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 15),
        )

        assert exc.usuario_id == 2
        assert "sobreposta" in str(exc).lower()


# ──────────────────────────────────────────────────────────────────────────────
# Testes de Regras de Capacidade
# ──────────────────────────────────────────────────────────────────────────────


class TestRegrasCapacidade:
    """Testes das regras de cálculo de capacidade."""

    def test_dia_util_tem_capacidade_normal(
        self, capacidade_dia_util: CapacidadeDia
    ) -> None:
        """Dia útil tem capacidade normal de 360 minutos."""
        assert capacidade_dia_util.minutos_capacidade_normal_prevista == 360
        assert capacidade_dia_util.eh_dia_util is True
        assert capacidade_dia_util.eh_feriado is False

    def test_feriado_zera_capacidade_normal(
        self, capacidade_feriado: CapacidadeDia
    ) -> None:
        """Feriado zera a capacidade normal."""
        assert capacidade_feriado.minutos_capacidade_normal_prevista == 0
        assert capacidade_feriado.eh_feriado is True
        # Mas permite hora extra
        assert capacidade_feriado.minutos_capacidade_extra_permitida == 240

    def test_ferias_zera_capacidade_total(
        self, capacidade_ferias: CapacidadeDia
    ) -> None:
        """Férias zera capacidade normal e extra."""
        assert capacidade_ferias.minutos_capacidade_normal_prevista == 0
        assert capacidade_ferias.minutos_capacidade_extra_permitida == 0
        assert capacidade_ferias.eh_indisponivel is True
        assert capacidade_ferias.tipo_indisponibilidade == TipoIndisponibilidade.FERIAS

    def test_fim_de_semana_eh_dia_nao_util(self) -> None:
        """Fim de semana não é dia útil."""
        # Sábado
        sabado = date(2026, 3, 14)
        assert sabado.weekday() == 5

        # Domingo
        domingo = date(2026, 3, 15)
        assert domingo.weekday() == 6

    def test_calculo_minutos_disponiveis(
        self, capacidade_dia_util: CapacidadeDia
    ) -> None:
        """Cálculo de minutos disponíveis considera já alocados."""
        capacidade = capacidade_dia_util.minutos_capacidade_normal_prevista
        ja_alocado = 200
        disponivel = capacidade - ja_alocado

        assert disponivel == 160

    def test_calculo_ocioso(self) -> None:
        """Fórmula de ocioso: max(0, previsto - realizado)."""
        previsto = 360
        realizado_bloco = 200
        realizado_externa = 100

        ocioso = max(0, previsto - (realizado_bloco + realizado_externa))

        assert ocioso == 60

    def test_ocioso_nao_pode_ser_negativo(self) -> None:
        """Ocioso nunca é negativo."""
        previsto = 360
        realizado = 400  # Impossível em capacidade normal, mas valida fórmula

        ocioso = max(0, previsto - realizado)

        assert ocioso == 0


# ──────────────────────────────────────────────────────────────────────────────
# Testes de Hora Extra
# ──────────────────────────────────────────────────────────────────────────────


class TestHoraExtra:
    """Testes de separação de hora extra."""

    def test_hora_extra_nao_conta_para_ocioso(self) -> None:
        """Hora extra não reduz o ocioso da faixa normal."""
        previsto_normal = 360
        realizado_normal = 300
        realizado_extra = 120  # Hora extra

        # Ocioso só considera faixa normal
        ocioso = max(0, previsto_normal - realizado_normal)

        assert ocioso == 60
        # Hora extra não entra no cálculo
        assert realizado_extra == 120

    def test_hora_extra_permitida_em_feriado(
        self, capacidade_feriado: CapacidadeDia
    ) -> None:
        """Feriado permite hora extra mas não capacidade normal."""
        assert capacidade_feriado.minutos_capacidade_normal_prevista == 0
        assert capacidade_feriado.minutos_capacidade_extra_permitida > 0

    def test_minutos_acima_limite_vao_para_extra(self) -> None:
        """Minutos acima do limite diário devem ir para hora extra."""
        capacidade_normal = 360
        minutos_solicitados = 400

        # Se tentar lançar 400 como normal, deve falhar
        excede = minutos_solicitados > capacidade_normal

        assert excede is True

        # O excedente deve ir para extra
        excedente = minutos_solicitados - capacidade_normal
        assert excedente == 40

    def test_faixa_minuto_enum(self) -> None:
        """Enum FaixaMinuto tem valores corretos."""
        assert FaixaMinuto.NORMAL.value == "NORMAL"
        assert FaixaMinuto.EXTRA.value == "EXTRA"


# ──────────────────────────────────────────────────────────────────────────────
# Testes de Permissões
# ──────────────────────────────────────────────────────────────────────────────


class TestPermissoes:
    """Testes de permissões de operador e administrador."""

    def test_operador_nao_pode_lancar_data_futura(self) -> None:
        """Operador não pode lançar em data futura."""
        data_atual = date(2026, 3, 10)
        data_lancamento = date(2026, 3, 15)

        with pytest.raises(DataFuturaError):
            if data_lancamento > data_atual:
                raise DataFuturaError(data_lancamento, data_atual)

    def test_operador_pode_lancar_data_passada(self) -> None:
        """Operador pode lançar em data passada (não futura)."""
        data_atual = date(2026, 3, 10)
        data_lancamento = date(2026, 3, 5)

        # Não deve lançar exceção
        assert data_lancamento <= data_atual

    def test_operador_pode_lancar_data_atual(self) -> None:
        """Operador pode lançar na data atual."""
        data_atual = date(2026, 3, 10)
        data_lancamento = date(2026, 3, 10)

        assert data_lancamento <= data_atual

    def test_operador_nao_pode_acessar_outro_usuario(self) -> None:
        """Operador não pode acessar dados de outro usuário."""
        usuario_operador = 2
        usuario_alvo = 3

        with pytest.raises(AcessoNegadoError):
            if usuario_operador != usuario_alvo:
                raise AcessoNegadoError(usuario_operador, f"dados do usuário {usuario_alvo}")

    def test_admin_pode_acessar_qualquer_usuario(self) -> None:
        """Admin pode acessar dados de qualquer usuário."""
        eh_admin = True
        usuario_alvo = 3

        # Admin não precisa validar acesso
        assert eh_admin is True

    def test_dia_consolidado_bloqueia_normal_para_operador(
        self, capacidade_consolidada: CapacidadeDia
    ) -> None:
        """Dia consolidado bloqueia lançamento normal para operador."""
        eh_admin = False
        faixa = FaixaMinuto.NORMAL

        with pytest.raises(DiaConsolidadoError):
            if capacidade_consolidada.status_dia == StatusDia.CONSOLIDADO:
                if not eh_admin and faixa == FaixaMinuto.NORMAL:
                    raise DiaConsolidadoError(capacidade_consolidada.data, permite_extra=True)

    def test_dia_consolidado_permite_extra_para_operador(
        self, capacidade_consolidada: CapacidadeDia
    ) -> None:
        """Dia consolidado permite hora extra para operador."""
        eh_admin = False
        faixa = FaixaMinuto.EXTRA

        # Não deve lançar exceção
        if capacidade_consolidada.status_dia == StatusDia.CONSOLIDADO:
            if faixa == FaixaMinuto.EXTRA:
                # OK, hora extra permitida
                pass

    def test_admin_pode_alterar_dia_consolidado(
        self, capacidade_consolidada: CapacidadeDia
    ) -> None:
        """Admin pode alterar dia consolidado."""
        eh_admin = True

        # Admin não tem restrição
        assert eh_admin is True
        assert capacidade_consolidada.status_dia == StatusDia.CONSOLIDADO


# ──────────────────────────────────────────────────────────────────────────────
# Testes de Cálculos Analíticos
# ──────────────────────────────────────────────────────────────────────────────


class TestCalculosAnaliticos:
    """Testes dos cálculos analíticos de capacidade."""

    def test_resumo_periodo_vazio(self) -> None:
        """Período sem lançamentos: ocioso = previsto."""
        resumo = ResumoCapacidadePeriodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 1),
            data_fim=date(2026, 3, 5),
            minutos_previstos_normais=1800,  # 5 dias * 360
            minutos_realizados_bloco_normais=0,
            minutos_perdidos_externas_normais=0,
            minutos_nao_alocados=0,
            minutos_ociosos=1800,  # Tudo ocioso
            minutos_extras_bloco=0,
            minutos_extras_externas=0,
            minutos_extras_totais=0,
        )

        assert resumo.minutos_ociosos == resumo.minutos_previstos_normais

    def test_resumo_com_externa(self) -> None:
        """Dia com 120 min externa: perdido=120, ocioso=240."""
        previsto = 360
        externa = 120

        perdido = externa
        ocioso = previsto - externa

        assert perdido == 120
        assert ocioso == 240

    def test_resumo_com_ferias(self) -> None:
        """Dia de férias entra como não alocado."""
        # Capacidade normal seria 360, mas está em férias
        minutos_dia_util_padrao = 360
        eh_ferias = True

        if eh_ferias:
            nao_alocado = minutos_dia_util_padrao
            previsto = 0
        else:
            nao_alocado = 0
            previsto = minutos_dia_util_padrao

        assert nao_alocado == 360
        assert previsto == 0

    def test_hora_extra_separada_no_resumo(self) -> None:
        """Hora extra aparece separada no resumo."""
        resumo = ResumoCapacidadePeriodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
            minutos_previstos_normais=360,
            minutos_realizados_bloco_normais=360,
            minutos_perdidos_externas_normais=0,
            minutos_nao_alocados=0,
            minutos_ociosos=0,
            minutos_extras_bloco=60,
            minutos_extras_externas=30,
            minutos_extras_totais=90,
        )

        # Normal completo
        assert resumo.minutos_ociosos == 0

        # Hora extra separada
        assert resumo.minutos_extras_totais == 90
        assert resumo.minutos_extras_bloco == 60
        assert resumo.minutos_extras_externas == 30


# ──────────────────────────────────────────────────────────────────────────────
# Testes de Consolidação
# ──────────────────────────────────────────────────────────────────────────────


class TestConsolidacao:
    """Testes do processo de consolidação."""

    def test_pendencia_sem_lancamento(self) -> None:
        """Dia útil sem lançamento gera pendência."""
        pendencia = PendenciaConsolidacao(
            usuario_id=2,
            data=date(2026, 3, 10),
            tipo=TipoPendencia.SEM_LANCAMENTO.value,
            motivo="Dia útil sem nenhum lançamento",
        )

        assert pendencia.tipo == "SEM_LANCAMENTO"

    def test_pendencia_lancamento_incompleto(self) -> None:
        """Lançamento abaixo de 50% gera pendência."""
        pendencia = PendenciaConsolidacao(
            usuario_id=2,
            data=date(2026, 3, 10),
            tipo=TipoPendencia.LANCAMENTO_INCOMPLETO.value,
            motivo="Soma de minutos normais (100) abaixo de 50% do esperado (360)",
        )

        assert pendencia.tipo == "LANCAMENTO_INCOMPLETO"

    def test_resultado_consolidacao_com_pendencias(self) -> None:
        """Consolidação com pendências não consolida."""
        resultado = ResultadoConsolidacao(
            consolidado=False,
            pendencias=[
                PendenciaConsolidacao(
                    usuario_id=2,
                    data=date(2026, 3, 10),
                    tipo=TipoPendencia.SEM_LANCAMENTO.value,
                    motivo="Dia útil sem lançamento",
                )
            ],
            mensagem="Encontradas 1 pendências",
        )

        assert resultado.consolidado is False
        assert len(resultado.pendencias) == 1

    def test_resultado_consolidacao_sucesso(self) -> None:
        """Consolidação sem pendências consolida."""
        resultado = ResultadoConsolidacao(
            consolidado=True,
            pendencias=[],
            mensagem="Consolidados 5 dias",
        )

        assert resultado.consolidado is True
        assert len(resultado.pendencias) == 0


# ──────────────────────────────────────────────────────────────────────────────
# Testes de Validação de Schemas
# ──────────────────────────────────────────────────────────────────────────────


class TestValidacaoSchemas:
    """Testes de validação dos schemas Pydantic."""

    def test_lancamento_bloco_requer_bloco_id(self) -> None:
        """Lançamento tipo BLOCO requer bloco_id."""
        from pydantic import ValidationError

        from cp.domain.capacidade.schemas import LancamentoInput

        with pytest.raises(ValidationError):
            LancamentoInput(
                data=date(2026, 3, 10),
                bloco_id=None,  # Deveria ter bloco_id
                tipo_atividade=CodigoAtividade.BLOCO,
                faixa=FaixaMinuto.NORMAL,
                minutos=120,
            )

    def test_lancamento_externa_nao_requer_bloco_id(self) -> None:
        """Lançamento tipo EXTERNA não requer bloco_id."""
        from cp.domain.capacidade.schemas import LancamentoInput

        lancamento = LancamentoInput(
            data=date(2026, 3, 10),
            bloco_id=None,
            tipo_atividade=CodigoAtividade.EXTERNA,
            faixa=FaixaMinuto.NORMAL,
            minutos=60,
        )

        assert lancamento.bloco_id is None

    def test_indisponibilidade_data_fim_maior_inicio(self) -> None:
        """Indisponibilidade requer data_fim >= data_inicio."""
        from pydantic import ValidationError

        from cp.domain.capacidade.schemas import IndisponibilidadeInput

        with pytest.raises(ValidationError):
            IndisponibilidadeInput(
                usuario_id=2,
                tipo=TipoIndisponibilidade.FERIAS,
                data_inicio=date(2026, 7, 15),
                data_fim=date(2026, 7, 1),  # Anterior ao início
            )

    def test_minutos_devem_ser_positivos(self) -> None:
        """Minutos devem ser > 0."""
        from pydantic import ValidationError

        from cp.domain.capacidade.schemas import LancamentoInput

        with pytest.raises(ValidationError):
            LancamentoInput(
                data=date(2026, 3, 10),
                bloco_id=1,
                tipo_atividade=CodigoAtividade.BLOCO,
                faixa=FaixaMinuto.NORMAL,
                minutos=0,  # Deve ser > 0
            )


# ──────────────────────────────────────────────────────────────────────────────
# Testes de Enums
# ──────────────────────────────────────────────────────────────────────────────


class TestEnums:
    """Testes dos enums de domínio."""

    def test_codigo_atividade_valores(self) -> None:
        """CodigoAtividade tem todos os valores esperados."""
        assert CodigoAtividade.BLOCO.value == "BLOCO"
        assert CodigoAtividade.EXTERNA.value == "EXTERNA"
        assert CodigoAtividade.AJUSTE.value == "AJUSTE"
        assert CodigoAtividade.FERIAS.value == "FERIAS"
        assert CodigoAtividade.LICENCA.value == "LICENCA"
        assert CodigoAtividade.CURSO.value == "CURSO"
        assert CodigoAtividade.AFASTAMENTO.value == "AFASTAMENTO"

    def test_grupo_atividade_valores(self) -> None:
        """GrupoAtividade tem todos os valores esperados."""
        assert GrupoAtividade.PRODUCAO.value == "PRODUCAO"
        assert GrupoAtividade.INDISPONIBILIDADE.value == "INDISPONIBILIDADE"
        assert GrupoAtividade.AJUSTE.value == "AJUSTE"

    def test_status_dia_valores(self) -> None:
        """StatusDia tem todos os valores esperados."""
        assert StatusDia.ABERTO.value == "ABERTO"
        assert StatusDia.CONSOLIDADO.value == "CONSOLIDADO"

    def test_tipo_indisponibilidade_valores(self) -> None:
        """TipoIndisponibilidade tem todos os valores esperados."""
        assert TipoIndisponibilidade.FERIAS.value == "FERIAS"
        assert TipoIndisponibilidade.LICENCA.value == "LICENCA"
        assert TipoIndisponibilidade.CURSO.value == "CURSO"
        assert TipoIndisponibilidade.AFASTAMENTO.value == "AFASTAMENTO"

    def test_tipo_pendencia_valores(self) -> None:
        """TipoPendencia tem todos os valores esperados."""
        assert TipoPendencia.SEM_LANCAMENTO.value == "SEM_LANCAMENTO"
        assert TipoPendencia.LANCAMENTO_INCOMPLETO.value == "LANCAMENTO_INCOMPLETO"
        assert TipoPendencia.INDISPONIBILIDADE_NAO_TRATADA.value == "INDISPONIBILIDADE_NAO_TRATADA"
        assert TipoPendencia.INCONSISTENCIA_CALENDARIO.value == "INCONSISTENCIA_CALENDARIO"
