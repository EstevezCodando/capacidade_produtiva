"""Testes completos do CapacidadeService.

Maximiza cobertura de código testando todos os métodos e branches.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from cp.domain.capacidade.enums import (
    CodigoAtividade,
    FaixaMinuto,
    GrupoAtividade,
    StatusDia,
    TipoIndisponibilidade,
)
from cp.domain.capacidade.exceptions import (
    RegistroNaoEncontradoError,
    VigenciaConflitanteError,
)
from cp.domain.capacidade.models import (
    AgendaLancamento,
    CapacidadeDia,
    ParametroCapacidade,
    TipoAtividade,
)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def mock_parametro(
    id: int = 1,
    minutos_dia: int = 360,
    minutos_extra: int = 240,
    data_inicio: date = date(2026, 1, 1),
    data_fim: date | None = None,
) -> Mock:
    m = Mock(spec=ParametroCapacidade)
    m.id = id
    m.minutos_dia_util_default = minutos_dia
    m.minutos_extra_maximo_default = minutos_extra
    m.data_inicio_vigencia = data_inicio
    m.data_fim_vigencia = data_fim
    m.criado_por = 1
    m.criado_em = datetime.now()
    return m


def mock_capacidade_dia(
    id: int = 1,
    usuario_id: int = 2,
    data: date = date(2026, 3, 10),
    minutos_normal: int = 360,
    minutos_extra: int = 240,
    eh_dia_util: bool = True,
    eh_feriado: bool = False,
    eh_indisponivel: bool = False,
    tipo_indisponibilidade: TipoIndisponibilidade | None = None,
    status: StatusDia = StatusDia.ABERTO,
) -> Mock:
    m = Mock(spec=CapacidadeDia)
    m.id = id
    m.usuario_id = usuario_id
    m.data = data
    m.minutos_capacidade_normal_prevista = minutos_normal
    m.minutos_capacidade_extra_permitida = minutos_extra
    m.eh_dia_util = eh_dia_util
    m.eh_feriado = eh_feriado
    m.eh_indisponivel = eh_indisponivel
    m.tipo_indisponibilidade = tipo_indisponibilidade
    m.status_dia = status
    m.origem_parametro_capacidade = 1
    m.atualizado_em = datetime.now()
    return m


def mock_tipo_atividade(
    id: int = 1,
    codigo: CodigoAtividade = CodigoAtividade.BLOCO,
) -> Mock:
    m = Mock(spec=TipoAtividade)
    m.id = id
    m.codigo = codigo
    m.nome = codigo.value
    m.grupo = GrupoAtividade.PRODUCAO
    return m


def mock_lancamento(
    id: int = 1,
    usuario_id: int = 2,
    data: date = date(2026, 3, 10),
    bloco_id: int | None = 1,
    tipo_atividade_id: int = 1,
    faixa: FaixaMinuto = FaixaMinuto.NORMAL,
    minutos: int = 120,
) -> Mock:
    m = Mock(spec=AgendaLancamento)
    m.id = id
    m.usuario_id = usuario_id
    m.data_lancamento = data
    m.bloco_id = bloco_id
    m.tipo_atividade_id = tipo_atividade_id
    m.faixa_minuto = faixa
    m.minutos = minutos
    return m


def mock_indisponibilidade(tipo_atividade_id: int = 4) -> Mock:
    m = Mock()
    m.tipo_atividade_id = tipo_atividade_id
    return m


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO CAPACIDADE SERVICE
# ══════════════════════════════════════════════════════════════════════════════


class TestCapacidadeServiceParametros:
    """Testes de gestão de parâmetros."""

    @pytest.fixture
    def service(self):
        """Cria CapacidadeService com mocks."""
        with patch("cp.services.capacidade.capacidade_service.ParametroCapacidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.capacidade_service.FeriadoRepository"), \
             patch("cp.services.capacidade.capacidade_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.capacidade_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AuditService"):
            
            from cp.services.capacidade.capacidade_service import CapacidadeService
            return CapacidadeService(MagicMock())

    def test_obter_parametro_vigente(self, service):
        """Obtém parâmetro vigente para a data."""
        param = mock_parametro()
        service._param_repo.buscar_vigente.return_value = param

        resultado = service.obter_parametro_vigente(date(2026, 3, 10))

        assert resultado == param
        service._param_repo.buscar_vigente.assert_called_once_with(date(2026, 3, 10))

    def test_obter_parametro_vigente_nenhum(self, service):
        """Retorna None se não há parâmetro vigente."""
        service._param_repo.buscar_vigente.return_value = None

        resultado = service.obter_parametro_vigente(date(2026, 3, 10))

        assert resultado is None

    def test_criar_parametro_sucesso(self, service):
        """Cria parâmetro com sucesso."""
        param = mock_parametro()
        service._param_repo.verificar_conflito_vigencia.return_value = False
        service._param_repo.criar.return_value = param

        resultado = service.criar_parametro(
            minutos_dia_util=360,
            minutos_extra_max=240,
            data_inicio=date(2026, 1, 1),
            data_fim=None,
            criado_por=1,
        )

        assert resultado == param
        service._audit.auditar_parametro_criado.assert_called_once()

    def test_criar_parametro_conflito_vigencia(self, service):
        """Erro se há conflito de vigência."""
        service._param_repo.verificar_conflito_vigencia.return_value = True

        with pytest.raises(VigenciaConflitanteError):
            service.criar_parametro(
                minutos_dia_util=360,
                minutos_extra_max=240,
                data_inicio=date(2026, 1, 1),
                data_fim=None,
                criado_por=1,
            )

    def test_atualizar_parametro_sucesso(self, service):
        """Atualiza parâmetro existente."""
        antes = mock_parametro(minutos_dia=360)
        depois = mock_parametro(minutos_dia=480)
        
        service._param_repo.buscar_por_id.return_value = antes
        service._param_repo.atualizar.return_value = depois

        resultado = service.atualizar_parametro(
            id=1,
            minutos_dia_util=480,
            minutos_extra_max=None,
            data_fim=None,
            atualizado_por=1,
        )

        assert resultado == depois
        service._audit.auditar_parametro_atualizado.assert_called_once()

    def test_atualizar_parametro_nao_encontrado(self, service):
        """Erro se parâmetro não existe."""
        service._param_repo.buscar_por_id.return_value = None

        with pytest.raises(RegistroNaoEncontradoError):
            service.atualizar_parametro(
                id=999,
                minutos_dia_util=480,
                minutos_extra_max=None,
                data_fim=None,
                atualizado_por=1,
            )


class TestCapacidadeServiceDiaUtil:
    """Testes do cálculo de dia útil."""

    @pytest.fixture
    def service(self):
        """Cria CapacidadeService com mocks."""
        with patch("cp.services.capacidade.capacidade_service.ParametroCapacidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.capacidade_service.FeriadoRepository"), \
             patch("cp.services.capacidade.capacidade_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.capacidade_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AuditService"):
            
            from cp.services.capacidade.capacidade_service import CapacidadeService
            return CapacidadeService(MagicMock())

    def test_eh_dia_util_segunda(self, service):
        """Segunda-feira é dia útil."""
        assert service._eh_dia_util(date(2026, 3, 9)) is True

    def test_eh_dia_util_terca(self, service):
        """Terça-feira é dia útil."""
        assert service._eh_dia_util(date(2026, 3, 10)) is True

    def test_eh_dia_util_quarta(self, service):
        """Quarta-feira é dia útil."""
        assert service._eh_dia_util(date(2026, 3, 11)) is True

    def test_eh_dia_util_quinta(self, service):
        """Quinta-feira é dia útil."""
        assert service._eh_dia_util(date(2026, 3, 12)) is True

    def test_eh_dia_util_sexta(self, service):
        """Sexta-feira é dia útil."""
        assert service._eh_dia_util(date(2026, 3, 13)) is True

    def test_eh_dia_util_sabado(self, service):
        """Sábado não é dia útil."""
        assert service._eh_dia_util(date(2026, 3, 14)) is False

    def test_eh_dia_util_domingo(self, service):
        """Domingo não é dia útil."""
        assert service._eh_dia_util(date(2026, 3, 15)) is False


class TestCapacidadeServiceTipoIndisponibilidade:
    """Testes do mapeamento de tipo de indisponibilidade."""

    @pytest.fixture
    def service(self):
        """Cria CapacidadeService com mocks."""
        with patch("cp.services.capacidade.capacidade_service.ParametroCapacidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.capacidade_service.FeriadoRepository"), \
             patch("cp.services.capacidade.capacidade_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.capacidade_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AuditService"):
            
            from cp.services.capacidade.capacidade_service import CapacidadeService
            return CapacidadeService(MagicMock())

    def test_obter_tipo_indisponibilidade_ferias(self, service):
        """FERIAS mapeia para TipoIndisponibilidade.FERIAS."""
        resultado = service._obter_tipo_indisponibilidade(CodigoAtividade.FERIAS)
        assert resultado == TipoIndisponibilidade.FERIAS

    def test_obter_tipo_indisponibilidade_licenca(self, service):
        """LICENCA mapeia para TipoIndisponibilidade.LICENCA."""
        resultado = service._obter_tipo_indisponibilidade(CodigoAtividade.LICENCA)
        assert resultado == TipoIndisponibilidade.LICENCA

    def test_obter_tipo_indisponibilidade_curso(self, service):
        """CURSO mapeia para TipoIndisponibilidade.CURSO."""
        resultado = service._obter_tipo_indisponibilidade(CodigoAtividade.CURSO)
        assert resultado == TipoIndisponibilidade.CURSO

    def test_obter_tipo_indisponibilidade_afastamento(self, service):
        """AFASTAMENTO mapeia para TipoIndisponibilidade.AFASTAMENTO."""
        resultado = service._obter_tipo_indisponibilidade(CodigoAtividade.AFASTAMENTO)
        assert resultado == TipoIndisponibilidade.AFASTAMENTO

    def test_obter_tipo_indisponibilidade_bloco_none(self, service):
        """BLOCO retorna None."""
        resultado = service._obter_tipo_indisponibilidade(CodigoAtividade.BLOCO)
        assert resultado is None

    def test_obter_tipo_indisponibilidade_externa_none(self, service):
        """EXTERNA retorna None."""
        resultado = service._obter_tipo_indisponibilidade(CodigoAtividade.EXTERNA)
        assert resultado is None

    def test_obter_tipo_indisponibilidade_ajuste_none(self, service):
        """AJUSTE retorna None."""
        resultado = service._obter_tipo_indisponibilidade(CodigoAtividade.AJUSTE)
        assert resultado is None


class TestCapacidadeServiceMaterializacao:
    """Testes da materialização de capacidade."""

    @pytest.fixture
    def service(self):
        """Cria CapacidadeService com mocks."""
        with patch("cp.services.capacidade.capacidade_service.ParametroCapacidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.capacidade_service.FeriadoRepository"), \
             patch("cp.services.capacidade.capacidade_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.capacidade_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AuditService"):
            
            from cp.services.capacidade.capacidade_service import CapacidadeService
            return CapacidadeService(MagicMock())

    def test_materializar_dia_util_normal(self, service):
        """Materializa dia útil normal com capacidade padrão."""
        param = mock_parametro()
        cap = mock_capacidade_dia()
        
        service._capacidade_repo.buscar.return_value = None
        service._param_repo.buscar_vigente.return_value = param
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None
        service._capacidade_repo.criar_ou_atualizar.return_value = cap

        resultado = service.materializar_capacidade_dia(2, date(2026, 3, 10), 1)

        assert resultado == cap
        call_args = service._capacidade_repo.criar_ou_atualizar.call_args
        assert call_args.kwargs["minutos_normal"] == 360
        assert call_args.kwargs["eh_dia_util"] is True

    def test_materializar_sem_parametro_usa_padrao(self, service):
        """Sem parâmetro vigente, usa valores padrão."""
        cap = mock_capacidade_dia()
        
        service._capacidade_repo.buscar.return_value = None
        service._param_repo.buscar_vigente.return_value = None  # Sem parâmetro
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None
        service._capacidade_repo.criar_ou_atualizar.return_value = cap

        service.materializar_capacidade_dia(2, date(2026, 3, 10), 1)

        call_args = service._capacidade_repo.criar_ou_atualizar.call_args
        assert call_args.kwargs["minutos_normal"] == 360  # Padrão
        assert call_args.kwargs["minutos_extra"] == 240  # Padrão

    def test_materializar_feriado(self, service):
        """Feriado tem capacidade normal zero."""
        param = mock_parametro()
        cap = mock_capacidade_dia(minutos_normal=0, eh_feriado=True)
        
        service._capacidade_repo.buscar.return_value = None
        service._param_repo.buscar_vigente.return_value = param
        service._feriado_repo.eh_feriado.return_value = True
        service._indisponibilidade_repo.buscar_para_data.return_value = None
        service._capacidade_repo.criar_ou_atualizar.return_value = cap

        service.materializar_capacidade_dia(2, date(2026, 4, 21), 1)

        call_args = service._capacidade_repo.criar_ou_atualizar.call_args
        assert call_args.kwargs["minutos_normal"] == 0
        assert call_args.kwargs["eh_feriado"] is True

    def test_materializar_fim_de_semana(self, service):
        """Fim de semana tem capacidade normal zero."""
        param = mock_parametro()
        cap = mock_capacidade_dia(minutos_normal=0, eh_dia_util=False)
        
        service._capacidade_repo.buscar.return_value = None
        service._param_repo.buscar_vigente.return_value = param
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None
        service._capacidade_repo.criar_ou_atualizar.return_value = cap

        service.materializar_capacidade_dia(2, date(2026, 3, 14), 1)  # Sábado

        call_args = service._capacidade_repo.criar_ou_atualizar.call_args
        assert call_args.kwargs["minutos_normal"] == 0
        assert call_args.kwargs["eh_dia_util"] is False

    def test_materializar_indisponibilidade(self, service):
        """Indisponibilidade tem capacidade normal zero."""
        param = mock_parametro()
        indisp = mock_indisponibilidade(tipo_atividade_id=4)
        tipo = mock_tipo_atividade(id=4, codigo=CodigoAtividade.FERIAS)
        cap = mock_capacidade_dia(minutos_normal=0, eh_indisponivel=True)
        
        service._capacidade_repo.buscar.return_value = None
        service._param_repo.buscar_vigente.return_value = param
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = indisp
        service._tipo_atividade_repo.buscar_por_id.return_value = tipo
        service._capacidade_repo.criar_ou_atualizar.return_value = cap

        service.materializar_capacidade_dia(2, date(2026, 7, 10), 1)

        call_args = service._capacidade_repo.criar_ou_atualizar.call_args
        assert call_args.kwargs["minutos_normal"] == 0
        assert call_args.kwargs["eh_indisponivel"] is True

    def test_materializar_mantem_status_consolidado(self, service):
        """Se já consolidado, mantém status."""
        param = mock_parametro()
        antes = mock_capacidade_dia(status=StatusDia.CONSOLIDADO)
        depois = mock_capacidade_dia(status=StatusDia.CONSOLIDADO)
        
        service._capacidade_repo.buscar.return_value = antes
        service._param_repo.buscar_vigente.return_value = param
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None
        service._capacidade_repo.criar_ou_atualizar.return_value = depois

        service.materializar_capacidade_dia(2, date(2026, 3, 10), 1)

        call_args = service._capacidade_repo.criar_ou_atualizar.call_args
        assert call_args.kwargs["status"] == StatusDia.CONSOLIDADO

    def test_materializar_periodo(self, service):
        """Materializa período de 5 dias."""
        param = mock_parametro()
        cap = mock_capacidade_dia()
        
        service._capacidade_repo.buscar.return_value = None
        service._param_repo.buscar_vigente.return_value = param
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None
        service._capacidade_repo.criar_ou_atualizar.return_value = cap

        resultado = service.materializar_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 9),  # Segunda
            data_fim=date(2026, 3, 13),    # Sexta
            executor_id=1,
        )

        assert len(resultado) == 5
        assert service._capacidade_repo.criar_ou_atualizar.call_count == 5


class TestCapacidadeServiceConsultas:
    """Testes das consultas de capacidade."""

    @pytest.fixture
    def service(self):
        """Cria CapacidadeService com mocks."""
        with patch("cp.services.capacidade.capacidade_service.ParametroCapacidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.capacidade_service.FeriadoRepository"), \
             patch("cp.services.capacidade.capacidade_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.capacidade_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AuditService"):
            
            from cp.services.capacidade.capacidade_service import CapacidadeService
            return CapacidadeService(MagicMock())

    def test_obter_capacidade_dia(self, service):
        """Obtém capacidade do dia."""
        cap = mock_capacidade_dia()
        service._capacidade_repo.buscar.return_value = cap

        resultado = service.obter_capacidade_dia(2, date(2026, 3, 10))

        assert resultado == cap

    def test_listar_capacidade_periodo(self, service):
        """Lista capacidades do período."""
        caps = [mock_capacidade_dia(id=1), mock_capacidade_dia(id=2)]
        service._capacidade_repo.listar_periodo.return_value = caps

        resultado = service.listar_capacidade_periodo(2, date(2026, 3, 1), date(2026, 3, 31))

        assert len(resultado) == 2


class TestCapacidadeServiceCalculos:
    """Testes dos cálculos analíticos."""

    @pytest.fixture
    def service(self):
        """Cria CapacidadeService com mocks."""
        with patch("cp.services.capacidade.capacidade_service.ParametroCapacidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.capacidade_service.FeriadoRepository"), \
             patch("cp.services.capacidade.capacidade_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.capacidade_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.capacidade_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.capacidade_service.AuditService"):
            
            from cp.services.capacidade.capacidade_service import CapacidadeService
            return CapacidadeService(MagicMock())

    def test_calcular_minutos_disponiveis_normal(self, service):
        """Calcula minutos disponíveis na faixa normal."""
        cap = mock_capacidade_dia(minutos_normal=360)
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.soma_minutos_dia.return_value = 200

        resultado = service.calcular_minutos_disponiveis_dia(
            usuario_id=2, data=date(2026, 3, 10), faixa=FaixaMinuto.NORMAL
        )

        assert resultado == 160  # 360 - 200

    def test_calcular_minutos_disponiveis_extra(self, service):
        """Calcula minutos disponíveis na faixa extra."""
        cap = mock_capacidade_dia(minutos_extra=240)
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.soma_minutos_dia.return_value = 100

        resultado = service.calcular_minutos_disponiveis_dia(
            usuario_id=2, data=date(2026, 3, 10), faixa=FaixaMinuto.EXTRA
        )

        assert resultado == 140  # 240 - 100

    def test_calcular_minutos_disponiveis_sem_capacidade(self, service):
        """Retorna zero se não há capacidade."""
        service._capacidade_repo.buscar.return_value = None

        resultado = service.calcular_minutos_disponiveis_dia(
            usuario_id=2, data=date(2026, 3, 10), faixa=FaixaMinuto.NORMAL
        )

        assert resultado == 0

    def test_calcular_minutos_disponiveis_esgotado(self, service):
        """Retorna zero se capacidade esgotada."""
        cap = mock_capacidade_dia(minutos_normal=360)
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.soma_minutos_dia.return_value = 400  # Mais que disponível

        resultado = service.calcular_minutos_disponiveis_dia(
            usuario_id=2, data=date(2026, 3, 10), faixa=FaixaMinuto.NORMAL
        )

        assert resultado == 0  # max(0, 360 - 400)

    def test_calcular_resumo_periodo_vazio(self, service):
        """Calcula resumo de período sem lançamentos."""
        caps = [
            mock_capacidade_dia(data=date(2026, 3, 10), minutos_normal=360),
            mock_capacidade_dia(data=date(2026, 3, 11), minutos_normal=360),
        ]
        
        service._capacidade_repo.listar_periodo.return_value = caps
        service._lancamento_repo.listar_por_usuario_periodo.return_value = []
        service._param_repo.buscar_vigente.return_value = mock_parametro()

        resultado = service.calcular_resumo_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 11),
        )

        assert resultado.minutos_previstos_normais == 720  # 360 * 2
        assert resultado.minutos_ociosos == 720  # Tudo ocioso

    def test_calcular_resumo_periodo_com_lancamentos(self, service):
        """Calcula resumo de período com lançamentos."""
        caps = [mock_capacidade_dia(data=date(2026, 3, 10), minutos_normal=360)]
        
        lanc_bloco = mock_lancamento(
            tipo_atividade_id=1, faixa=FaixaMinuto.NORMAL, minutos=200
        )
        lanc_externa = mock_lancamento(
            tipo_atividade_id=2, faixa=FaixaMinuto.NORMAL, minutos=100
        )
        
        service._capacidade_repo.listar_periodo.return_value = caps
        service._lancamento_repo.listar_por_usuario_periodo.return_value = [lanc_bloco, lanc_externa]
        service._tipo_atividade_repo.buscar_por_id.side_effect = lambda id: {
            1: mock_tipo_atividade(id=1, codigo=CodigoAtividade.BLOCO),
            2: mock_tipo_atividade(id=2, codigo=CodigoAtividade.EXTERNA),
        }.get(id)

        resultado = service.calcular_resumo_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert resultado.minutos_previstos_normais == 360
        assert resultado.minutos_realizados_bloco_normais == 200
        assert resultado.minutos_perdidos_externas_normais == 100
        assert resultado.minutos_ociosos == 60  # 360 - 200 - 100

    def test_calcular_resumo_periodo_com_horas_extras(self, service):
        """Calcula resumo com horas extras."""
        caps = [mock_capacidade_dia(data=date(2026, 3, 10), minutos_normal=360)]
        
        lanc_normal = mock_lancamento(
            tipo_atividade_id=1, faixa=FaixaMinuto.NORMAL, minutos=360
        )
        lanc_extra = mock_lancamento(
            tipo_atividade_id=1, faixa=FaixaMinuto.EXTRA, minutos=60
        )
        
        service._capacidade_repo.listar_periodo.return_value = caps
        service._lancamento_repo.listar_por_usuario_periodo.return_value = [lanc_normal, lanc_extra]
        service._tipo_atividade_repo.buscar_por_id.return_value = mock_tipo_atividade(
            id=1, codigo=CodigoAtividade.BLOCO
        )

        resultado = service.calcular_resumo_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert resultado.minutos_realizados_bloco_normais == 360
        assert resultado.minutos_extras_bloco == 60
        assert resultado.minutos_extras_totais == 60
        assert resultado.minutos_ociosos == 0

    def test_calcular_resumo_periodo_com_indisponibilidade(self, service):
        """Calcula resumo com dia indisponível."""
        caps = [
            mock_capacidade_dia(
                data=date(2026, 7, 10),
                minutos_normal=0,
                eh_indisponivel=True,
                eh_dia_util=True,
                eh_feriado=False,
            )
        ]
        
        service._capacidade_repo.listar_periodo.return_value = caps
        service._lancamento_repo.listar_por_usuario_periodo.return_value = []
        service._param_repo.buscar_vigente.return_value = mock_parametro()

        resultado = service.calcular_resumo_periodo(
            usuario_id=2,
            data_inicio=date(2026, 7, 10),
            data_fim=date(2026, 7, 10),
        )

        assert resultado.minutos_nao_alocados == 360  # Seria capacidade normal

    def test_calcular_resumo_periodo_filtro_bloco(self, service):
        """Calcula resumo filtrando por bloco."""
        caps = [mock_capacidade_dia(data=date(2026, 3, 10), minutos_normal=360)]
        
        lanc_bloco1 = mock_lancamento(bloco_id=1, minutos=200)
        lanc_bloco2 = mock_lancamento(bloco_id=2, minutos=100)
        
        service._capacidade_repo.listar_periodo.return_value = caps
        service._lancamento_repo.listar_por_usuario_periodo.return_value = [lanc_bloco1, lanc_bloco2]
        service._tipo_atividade_repo.buscar_por_id.return_value = mock_tipo_atividade()

        resultado = service.calcular_resumo_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
            bloco_id=1,  # Filtrar só bloco 1
        )

        assert resultado.minutos_realizados_bloco_normais == 200  # Só bloco 1

    def test_calcular_resumo_periodo_tipo_ajuste(self, service):
        """Calcula resumo com tipo AJUSTE."""
        caps = [mock_capacidade_dia(data=date(2026, 3, 10), minutos_normal=360)]
        
        lanc_ajuste = mock_lancamento(tipo_atividade_id=3, faixa=FaixaMinuto.NORMAL, minutos=50)
        
        service._capacidade_repo.listar_periodo.return_value = caps
        service._lancamento_repo.listar_por_usuario_periodo.return_value = [lanc_ajuste]
        service._tipo_atividade_repo.buscar_por_id.return_value = mock_tipo_atividade(
            id=3, codigo=CodigoAtividade.AJUSTE
        )

        resultado = service.calcular_resumo_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert resultado.minutos_ociosos == 310  # 360 - 50

    def test_calcular_resumo_periodo_tipo_nao_encontrado(self, service):
        """Ignora lançamentos com tipo não encontrado."""
        caps = [mock_capacidade_dia(data=date(2026, 3, 10), minutos_normal=360)]
        
        lanc = mock_lancamento(tipo_atividade_id=999, minutos=100)
        
        service._capacidade_repo.listar_periodo.return_value = caps
        service._lancamento_repo.listar_por_usuario_periodo.return_value = [lanc]
        service._tipo_atividade_repo.buscar_por_id.return_value = None

        resultado = service.calcular_resumo_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        # Lançamento ignorado
        assert resultado.minutos_ociosos == 360
