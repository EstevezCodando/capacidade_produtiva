"""Testes do ConsolidacaoService e AuditService.

Maximiza cobertura de código testando todos os métodos e branches.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest

from cp.domain.capacidade.enums import (
    AcaoAuditoria,
    FaixaMinuto,
    StatusDia,
    TipoPendencia,
)
from cp.domain.capacidade.exceptions import (
    IntervaloInvalidoError,
)
from cp.domain.capacidade.models import (
    AgendaLancamento,
    CapacidadeDia,
)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def mock_capacidade_dia(
    id: int = 1,
    usuario_id: int = 2,
    data: date = date(2026, 3, 10),
    minutos_normal: int = 360,
    eh_dia_util: bool = True,
    eh_feriado: bool = False,
    eh_indisponivel: bool = False,
    status: StatusDia = StatusDia.ABERTO,
) -> Mock:
    m = Mock(spec=CapacidadeDia)
    m.id = id
    m.usuario_id = usuario_id
    m.data = data
    m.minutos_capacidade_normal_prevista = minutos_normal
    m.eh_dia_util = eh_dia_util
    m.eh_feriado = eh_feriado
    m.eh_indisponivel = eh_indisponivel
    m.status_dia = status
    return m


def mock_lancamento(
    id: int = 1,
    faixa: FaixaMinuto = FaixaMinuto.NORMAL,
    minutos: int = 120,
) -> Mock:
    m = Mock(spec=AgendaLancamento)
    m.id = id
    m.faixa_minuto = faixa
    m.minutos = minutos
    return m


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO CONSOLIDACAO SERVICE
# ══════════════════════════════════════════════════════════════════════════════


class TestConsolidacaoServicePendencias:
    """Testes de verificação de pendências."""

    @pytest.fixture
    def service(self):
        """Cria ConsolidacaoService com mocks."""
        with patch("cp.services.capacidade.consolidacao_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.consolidacao_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.consolidacao_service.FeriadoRepository"), \
             patch("cp.services.capacidade.consolidacao_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.consolidacao_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.consolidacao_service.AuditService"):
            
            from cp.services.capacidade.consolidacao_service import ConsolidacaoService
            return ConsolidacaoService(MagicMock())

    def test_verificar_pendencias_intervalo_invalido(self, service):
        """Erro se data_fim < data_inicio."""
        with pytest.raises(IntervaloInvalidoError):
            service.verificar_pendencias(
                usuario_id=2,
                data_inicio=date(2026, 3, 15),
                data_fim=date(2026, 3, 10),
            )

    def test_verificar_pendencias_sem_capacidade_dia_util(self, service):
        """Dia útil sem capacidade gera pendência."""
        service._capacidade_repo.buscar.return_value = None
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),  # Terça
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 1
        assert pendencias[0].tipo == TipoPendencia.SEM_LANCAMENTO.value

    def test_verificar_pendencias_sem_capacidade_fim_semana_ok(self, service):
        """Fim de semana sem capacidade não gera pendência."""
        service._capacidade_repo.buscar.return_value = None
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 14),  # Sábado
            data_fim=date(2026, 3, 14),
        )

        assert len(pendencias) == 0

    def test_verificar_pendencias_sem_capacidade_feriado_ok(self, service):
        """Feriado sem capacidade não gera pendência."""
        service._capacidade_repo.buscar.return_value = None
        service._feriado_repo.eh_feriado.return_value = True
        service._indisponibilidade_repo.buscar_para_data.return_value = None

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 4, 21),  # Tiradentes
            data_fim=date(2026, 4, 21),
        )

        assert len(pendencias) == 0

    def test_verificar_pendencias_sem_capacidade_indisponivel_ok(self, service):
        """Dia com indisponibilidade sem capacidade não gera pendência."""
        service._capacidade_repo.buscar.return_value = None
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = Mock()

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 7, 10),
            data_fim=date(2026, 7, 10),
        )

        assert len(pendencias) == 0

    def test_verificar_pendencias_dia_consolidado_pula(self, service):
        """Dias já consolidados são pulados."""
        cap = mock_capacidade_dia(status=StatusDia.CONSOLIDADO)
        service._capacidade_repo.buscar.return_value = cap

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 0

    def test_verificar_pendencias_dia_indisponivel_sem_cadastro(self, service):
        """Dia indisponível sem cadastro gera pendência."""
        cap = mock_capacidade_dia(eh_indisponivel=True)
        service._capacidade_repo.buscar.return_value = cap
        service._indisponibilidade_repo.buscar_para_data.return_value = None

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 1
        assert pendencias[0].tipo == TipoPendencia.INDISPONIBILIDADE_NAO_TRATADA.value

    def test_verificar_pendencias_dia_indisponivel_com_cadastro_ok(self, service):
        """Dia indisponível com cadastro não gera pendência."""
        cap = mock_capacidade_dia(eh_indisponivel=True)
        service._capacidade_repo.buscar.return_value = cap
        service._indisponibilidade_repo.buscar_para_data.return_value = Mock()

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 0

    def test_verificar_pendencias_dia_util_sem_lancamentos(self, service):
        """Dia útil sem lançamentos gera pendência."""
        cap = mock_capacidade_dia(eh_dia_util=True, eh_feriado=False)
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.listar_por_dia.return_value = []

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 1
        assert pendencias[0].tipo == TipoPendencia.SEM_LANCAMENTO.value

    def test_verificar_pendencias_dia_util_com_lancamentos_ok(self, service):
        """Dia útil com lançamentos suficientes não gera pendência."""
        cap = mock_capacidade_dia(minutos_normal=360)
        lanc = mock_lancamento(minutos=200)  # Mais de 50%
        
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.listar_por_dia.return_value = [lanc]

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 0

    def test_verificar_pendencias_lancamento_incompleto(self, service):
        """Lançamento abaixo de 50% gera pendência."""
        cap = mock_capacidade_dia(minutos_normal=360)
        lanc = mock_lancamento(minutos=100)  # Menos de 50% de 360
        
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.listar_por_dia.return_value = [lanc]

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 1
        assert pendencias[0].tipo == TipoPendencia.LANCAMENTO_INCOMPLETO.value

    def test_verificar_pendencias_feriado_pula(self, service):
        """Feriado é pulado mesmo com capacidade."""
        cap = mock_capacidade_dia(eh_dia_util=True, eh_feriado=True)
        service._capacidade_repo.buscar.return_value = cap

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 0

    def test_verificar_pendencias_fim_semana_pula(self, service):
        """Fim de semana é pulado."""
        cap = mock_capacidade_dia(eh_dia_util=False, eh_feriado=False)
        service._capacidade_repo.buscar.return_value = cap

        pendencias = service.verificar_pendencias(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 0

    def test_verificar_pendencias_todos_usuarios(self, service):
        """Verifica pendências de múltiplos usuários."""
        cap = mock_capacidade_dia(eh_dia_util=True, eh_feriado=False)
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.listar_por_dia.return_value = []

        pendencias = service.verificar_pendencias_todos_usuarios(
            usuarios_ids=[2, 3],
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
        )

        assert len(pendencias) == 2


class TestConsolidacaoServiceConsolidar:
    """Testes da consolidação."""

    @pytest.fixture
    def service(self):
        """Cria ConsolidacaoService com mocks."""
        with patch("cp.services.capacidade.consolidacao_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.consolidacao_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.consolidacao_service.FeriadoRepository"), \
             patch("cp.services.capacidade.consolidacao_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.consolidacao_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.consolidacao_service.AuditService"):
            
            from cp.services.capacidade.consolidacao_service import ConsolidacaoService
            return ConsolidacaoService(MagicMock())

    def test_consolidar_periodo_intervalo_invalido(self, service):
        """Erro se data_fim < data_inicio."""
        with pytest.raises(IntervaloInvalidoError):
            service.consolidar_periodo(
                usuario_id=2,
                data_inicio=date(2026, 3, 15),
                data_fim=date(2026, 3, 10),
                executor_id=1,
            )

    def test_consolidar_periodo_com_pendencias_bloqueado(self, service):
        """Consolidação bloqueada se há pendências."""
        cap = mock_capacidade_dia(eh_dia_util=True, eh_feriado=False)
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.listar_por_dia.return_value = []

        resultado = service.consolidar_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
            executor_id=1,
            ignorar_pendencias=False,
        )

        assert resultado.consolidado is False
        assert len(resultado.pendencias) > 0

    def test_consolidar_periodo_ignorando_pendencias(self, service):
        """Consolidação forçada ignorando pendências."""
        cap = mock_capacidade_dia(eh_dia_util=True, eh_feriado=False)
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.listar_por_dia.return_value = []
        service._capacidade_repo.consolidar_periodo.return_value = 1

        resultado = service.consolidar_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
            executor_id=1,
            ignorar_pendencias=True,
        )

        assert resultado.consolidado is True
        service._audit.registrar_consolidacao.assert_called_once()

    def test_consolidar_periodo_sem_pendencias_sucesso(self, service):
        """Consolidação bem sucedida sem pendências."""
        cap = mock_capacidade_dia(minutos_normal=360)
        lanc = mock_lancamento(minutos=200)
        
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.listar_por_dia.return_value = [lanc]
        service._capacidade_repo.consolidar_periodo.return_value = 1

        resultado = service.consolidar_periodo(
            usuario_id=2,
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
            executor_id=1,
        )

        assert resultado.consolidado is True

    def test_consolidar_periodo_todos_usuarios_com_pendencias(self, service):
        """Consolidação de múltiplos usuários bloqueada se há pendências."""
        cap = mock_capacidade_dia(eh_dia_util=True, eh_feriado=False)
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.listar_por_dia.return_value = []

        resultado = service.consolidar_periodo_todos_usuarios(
            usuarios_ids=[2, 3],
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
            executor_id=1,
            ignorar_pendencias=False,
        )

        assert resultado.consolidado is False

    def test_consolidar_periodo_todos_usuarios_sucesso(self, service):
        """Consolidação de múltiplos usuários com sucesso."""
        cap = mock_capacidade_dia(minutos_normal=360)
        lanc = mock_lancamento(minutos=200)
        
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.listar_por_dia.return_value = [lanc]
        service._capacidade_repo.consolidar_periodo.return_value = 1

        resultado = service.consolidar_periodo_todos_usuarios(
            usuarios_ids=[2, 3],
            data_inicio=date(2026, 3, 10),
            data_fim=date(2026, 3, 10),
            executor_id=1,
        )

        assert resultado.consolidado is True
        assert service._capacidade_repo.consolidar_periodo.call_count == 2

    def test_consolidar_periodo_todos_usuarios_intervalo_invalido(self, service):
        """Erro se intervalo inválido."""
        with pytest.raises(IntervaloInvalidoError):
            service.consolidar_periodo_todos_usuarios(
                usuarios_ids=[2],
                data_inicio=date(2026, 3, 15),
                data_fim=date(2026, 3, 10),
                executor_id=1,
            )

    def test_obter_status_dias(self, service):
        """Obtém status dos dias no período."""
        caps = [
            mock_capacidade_dia(data=date(2026, 3, 10), status=StatusDia.ABERTO),
            mock_capacidade_dia(data=date(2026, 3, 11), status=StatusDia.CONSOLIDADO),
        ]
        service._capacidade_repo.listar_por_status.return_value = caps

        resultado = service.obter_status_dias(date(2026, 3, 10), date(2026, 3, 11))

        assert len(resultado) == 2


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO AUDIT SERVICE
# ══════════════════════════════════════════════════════════════════════════════


class TestAuditService:
    """Testes do AuditService."""

    @pytest.fixture
    def service(self):
        """Cria AuditService com mocks."""
        with patch("cp.services.capacidade.audit_service.AuditLogRepository"):
            from cp.services.capacidade.audit_service import AuditService
            return AuditService(MagicMock())

    def test_serializar_modelo(self, service):
        """Serializa modelo para JSON."""
        modelo = Mock()
        modelo.id = 1
        modelo.nome = "teste"

        resultado = service._serializar_modelo(modelo)

        assert isinstance(resultado, dict)

    def test_serializar_modelo_none(self, service):
        """Serializa None retorna dict vazio."""
        resultado = service._serializar_modelo(None)

        assert resultado == {}

    def test_registrar_criacao(self, service):
        """Registra criação de entidade."""
        modelo = Mock()
        modelo.id = 1

        service.registrar_criacao(
            entidade="teste",
            entidade_id=1,
            modelo=modelo,
            usuario_executor=1,
        )

        service._repo.registrar.assert_called_once()
        call_args = service._repo.registrar.call_args
        assert call_args.kwargs["acao"] == AcaoAuditoria.CREATE
        assert call_args.kwargs["antes"] is None

    def test_registrar_atualizacao(self, service):
        """Registra atualização de entidade."""
        antes = Mock()
        depois = Mock()

        service.registrar_atualizacao(
            entidade="teste",
            entidade_id=1,
            antes=antes,
            depois=depois,
            usuario_executor=1,
        )

        service._repo.registrar.assert_called_once()
        call_args = service._repo.registrar.call_args
        assert call_args.kwargs["acao"] == AcaoAuditoria.UPDATE

    def test_registrar_exclusao(self, service):
        """Registra exclusão de entidade."""
        modelo = Mock()

        service.registrar_exclusao(
            entidade="teste",
            entidade_id=1,
            modelo=modelo,
            usuario_executor=1,
        )

        service._repo.registrar.assert_called_once()
        call_args = service._repo.registrar.call_args
        assert call_args.kwargs["acao"] == AcaoAuditoria.DELETE
        assert call_args.kwargs["depois"] is None

    def test_registrar_consolidacao(self, service):
        """Registra consolidação de período."""
        service.registrar_consolidacao(
            data_inicio=date(2026, 3, 1),
            data_fim=date(2026, 3, 15),
            usuarios_afetados=[2, 3, 4],
            usuario_executor=1,
        )

        service._repo.registrar.assert_called_once()
        call_args = service._repo.registrar.call_args
        assert call_args.kwargs["acao"] == AcaoAuditoria.CONSOLIDATE

    def test_auditar_parametro_criado(self, service):
        """Audita criação de parâmetro."""
        param = Mock()
        param.id = 1

        service.auditar_parametro_criado(param, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_parametro_atualizado(self, service):
        """Audita atualização de parâmetro."""
        antes = Mock()
        antes.id = 1
        depois = Mock()
        depois.id = 1

        service.auditar_parametro_atualizado(antes, depois, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_planejamento_criado(self, service):
        """Audita criação de planejamento."""
        plan = Mock()
        plan.id = 1

        service.auditar_planejamento_criado(plan, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_planejamento_atualizado(self, service):
        """Audita atualização de planejamento."""
        antes = Mock()
        antes.id = 1
        depois = Mock()
        depois.id = 1

        service.auditar_planejamento_atualizado(antes, depois, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_planejamento_removido(self, service):
        """Audita remoção de planejamento."""
        plan = Mock()
        plan.id = 1

        service.auditar_planejamento_removido(plan, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_lancamento_criado(self, service):
        """Audita criação de lançamento."""
        lanc = Mock()
        lanc.id = 1

        service.auditar_lancamento_criado(lanc, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_lancamento_atualizado(self, service):
        """Audita atualização de lançamento."""
        antes = Mock()
        antes.id = 1
        depois = Mock()
        depois.id = 1

        service.auditar_lancamento_atualizado(antes, depois, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_lancamento_removido(self, service):
        """Audita remoção de lançamento."""
        lanc = Mock()
        lanc.id = 1

        service.auditar_lancamento_removido(lanc, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_feriado_criado(self, service):
        """Audita criação de feriado."""
        feriado = Mock()
        feriado.id = 1

        service.auditar_feriado_criado(feriado, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_feriado_removido(self, service):
        """Audita remoção de feriado."""
        feriado = Mock()
        feriado.id = 1

        service.auditar_feriado_removido(feriado, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_indisponibilidade_criada(self, service):
        """Audita criação de indisponibilidade."""
        indisp = Mock()
        indisp.id = 1

        service.auditar_indisponibilidade_criada(indisp, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_indisponibilidade_removida(self, service):
        """Audita remoção de indisponibilidade."""
        indisp = Mock()
        indisp.id = 1

        service.auditar_indisponibilidade_removida(indisp, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_capacidade_dia_atualizada_nova(self, service):
        """Audita criação de capacidade dia."""
        depois = Mock()
        depois.id = 1

        service.auditar_capacidade_dia_atualizada(None, depois, 1)

        service._repo.registrar.assert_called_once()

    def test_auditar_capacidade_dia_atualizada_existente(self, service):
        """Audita atualização de capacidade dia."""
        antes = Mock()
        antes.id = 1
        depois = Mock()
        depois.id = 1

        service.auditar_capacidade_dia_atualizada(antes, depois, 1)

        service._repo.registrar.assert_called_once()
