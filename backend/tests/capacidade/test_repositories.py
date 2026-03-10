"""Testes dos repositórios de Capacidade.

Testa as operações de banco de dados usando mocks de sessão.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, Mock, patch

from cp.domain.capacidade.enums import (
    AcaoAuditoria,
    CodigoAtividade,
    FaixaMinuto,
    StatusDia,
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

# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO TIPO ATIVIDADE REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════


class TestTipoAtividadeRepository:
    """Testes do TipoAtividadeRepository."""

    def test_buscar_por_codigo(self):
        """Busca tipo por código."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            tipo_mock = Mock(spec=TipoAtividade)
            tipo_mock.codigo = CodigoAtividade.BLOCO
            mock_session.execute.return_value.scalar_one_or_none.return_value = tipo_mock

            from src.cp.repositories.capacidade.repositories import TipoAtividadeRepository
            repo = TipoAtividadeRepository(MagicMock())
            resultado = repo.buscar_por_codigo(CodigoAtividade.BLOCO)

            assert resultado == tipo_mock

    def test_buscar_por_codigo_nao_encontrado(self):
        """Retorna None se não encontrado."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = None

            from src.cp.repositories.capacidade.repositories import TipoAtividadeRepository
            repo = TipoAtividadeRepository(MagicMock())
            resultado = repo.buscar_por_codigo(CodigoAtividade.BLOCO)

            assert resultado is None

    def test_listar_todos(self):
        """Lista todos os tipos."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            tipos = [Mock(spec=TipoAtividade), Mock(spec=TipoAtividade)]
            mock_session.execute.return_value.scalars.return_value.all.return_value = tipos

            from src.cp.repositories.capacidade.repositories import TipoAtividadeRepository
            repo = TipoAtividadeRepository(MagicMock())
            resultado = repo.listar_todos()

            assert len(resultado) == 2

    def test_buscar_por_id(self):
        """Busca tipo por ID."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            tipo_mock = Mock(spec=TipoAtividade)
            tipo_mock.id = 1
            mock_session.get.return_value = tipo_mock

            from src.cp.repositories.capacidade.repositories import TipoAtividadeRepository
            repo = TipoAtividadeRepository(MagicMock())
            resultado = repo.buscar_por_id(1)

            assert resultado == tipo_mock


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO PARAMETRO CAPACIDADE REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════


class TestParametroCapacidadeRepository:
    """Testes do ParametroCapacidadeRepository."""

    def test_buscar_vigente(self):
        """Busca parâmetro vigente."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            param = Mock(spec=ParametroCapacidade)
            mock_session.execute.return_value.scalar_one_or_none.return_value = param

            from src.cp.repositories.capacidade.repositories import ParametroCapacidadeRepository
            repo = ParametroCapacidadeRepository(MagicMock())
            resultado = repo.buscar_vigente(date(2026, 3, 10))

            assert resultado == param

    def test_buscar_por_id(self):
        """Busca parâmetro por ID."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            param = Mock(spec=ParametroCapacidade)
            param.id = 1
            mock_session.get.return_value = param

            from src.cp.repositories.capacidade.repositories import ParametroCapacidadeRepository
            repo = ParametroCapacidadeRepository(MagicMock())
            resultado = repo.buscar_por_id(1)

            assert resultado == param

    def test_criar(self):
        """Cria novo parâmetro."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)

            from src.cp.repositories.capacidade.repositories import ParametroCapacidadeRepository
            repo = ParametroCapacidadeRepository(MagicMock())
            
            repo.criar(
                minutos_dia_util=360,
                minutos_extra_max=240,
                data_inicio=date(2026, 1, 1),
                data_fim=None,
                criado_por=1,
            )

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_verificar_conflito_vigencia_sem_conflito(self):
        """Sem conflito de vigência."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = None

            from src.cp.repositories.capacidade.repositories import ParametroCapacidadeRepository
            repo = ParametroCapacidadeRepository(MagicMock())
            resultado = repo.verificar_conflito_vigencia(date(2026, 1, 1), None)

            assert resultado is False

    def test_verificar_conflito_vigencia_com_conflito(self):
        """Com conflito de vigência."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = Mock()

            from src.cp.repositories.capacidade.repositories import ParametroCapacidadeRepository
            repo = ParametroCapacidadeRepository(MagicMock())
            resultado = repo.verificar_conflito_vigencia(date(2026, 1, 1), None)

            assert resultado is True

    def test_atualizar(self):
        """Atualiza parâmetro existente."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            param = Mock(spec=ParametroCapacidade)
            param.id = 1
            param.minutos_dia_util_default = 360
            mock_session.get.return_value = param

            from src.cp.repositories.capacidade.repositories import ParametroCapacidadeRepository
            repo = ParametroCapacidadeRepository(MagicMock())
            repo.atualizar(id=1, minutos_dia_util=480, minutos_extra_max=None, data_fim=None)

            mock_session.commit.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO CAPACIDADE DIA REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════


class TestCapacidadeDiaRepository:
    """Testes do CapacidadeDiaRepository."""

    def test_buscar(self):
        """Busca capacidade por usuário e data."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            cap = Mock(spec=CapacidadeDia)
            mock_session.execute.return_value.scalar_one_or_none.return_value = cap

            from src.cp.repositories.capacidade.repositories import CapacidadeDiaRepository
            repo = CapacidadeDiaRepository(MagicMock())
            resultado = repo.buscar(2, date(2026, 3, 10))

            assert resultado == cap

    def test_listar_periodo(self):
        """Lista capacidades do período."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            caps = [Mock(spec=CapacidadeDia), Mock(spec=CapacidadeDia)]
            mock_session.execute.return_value.scalars.return_value.all.return_value = caps

            from src.cp.repositories.capacidade.repositories import CapacidadeDiaRepository
            repo = CapacidadeDiaRepository(MagicMock())
            resultado = repo.listar_periodo(2, date(2026, 3, 1), date(2026, 3, 31))

            assert len(resultado) == 2

    def test_criar_ou_atualizar_novo(self):
        """Cria nova capacidade."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = None

            from src.cp.repositories.capacidade.repositories import CapacidadeDiaRepository
            repo = CapacidadeDiaRepository(MagicMock())
            
            repo.criar_ou_atualizar(
                usuario_id=2,
                data=date(2026, 3, 10),
                minutos_normal=360,
                minutos_extra=240,
                eh_dia_util=True,
                eh_feriado=False,
                eh_indisponivel=False,
                tipo_indisponibilidade=None,
                status=StatusDia.ABERTO,
                origem_parametro=1,
            )

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_consolidar_periodo(self):
        """Consolida período."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.rowcount = 5

            from src.cp.repositories.capacidade.repositories import CapacidadeDiaRepository
            repo = CapacidadeDiaRepository(MagicMock())
            resultado = repo.consolidar_periodo(2, date(2026, 3, 1), date(2026, 3, 15))

            assert resultado == 5


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO AGENDA PREVISTA REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════


class TestAgendaPrevistaRepository:
    """Testes do AgendaPrevistaRepository."""

    def test_buscar_existente(self):
        """Busca planejamento existente."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            plan = Mock(spec=AgendaPrevistaAdmin)
            mock_session.execute.return_value.scalar_one_or_none.return_value = plan

            from src.cp.repositories.capacidade.repositories import AgendaPrevistaRepository
            repo = AgendaPrevistaRepository(MagicMock())
            resultado = repo.buscar_existente(2, date(2026, 3, 10), 1)

            assert resultado == plan

    def test_criar(self):
        """Cria novo planejamento."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)

            from src.cp.repositories.capacidade.repositories import AgendaPrevistaRepository
            repo = AgendaPrevistaRepository(MagicMock())
            
            repo.criar(
                usuario_id=2,
                data=date(2026, 3, 10),
                bloco_id=1,
                minutos_normais=120,
                minutos_extras=0,
                descricao=None,
                criado_por=1,
            )

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_buscar_por_id(self):
        """Busca planejamento por ID."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            plan = Mock(spec=AgendaPrevistaAdmin)
            plan.id = 1
            mock_session.get.return_value = plan

            from src.cp.repositories.capacidade.repositories import AgendaPrevistaRepository
            repo = AgendaPrevistaRepository(MagicMock())
            resultado = repo.buscar_por_id(1)

            assert resultado == plan

    def test_atualizar(self):
        """Atualiza planejamento."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            plan = Mock(spec=AgendaPrevistaAdmin)
            plan.id = 1
            mock_session.get.return_value = plan

            from src.cp.repositories.capacidade.repositories import AgendaPrevistaRepository
            repo = AgendaPrevistaRepository(MagicMock())
            repo.atualizar(id=1, minutos_normais=180, minutos_extras=None, descricao=None)

            mock_session.commit.assert_called_once()

    def test_remover(self):
        """Remove planejamento."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            plan = Mock(spec=AgendaPrevistaAdmin)
            mock_session.get.return_value = plan

            from src.cp.repositories.capacidade.repositories import AgendaPrevistaRepository
            repo = AgendaPrevistaRepository(MagicMock())
            resultado = repo.remover(1)

            mock_session.delete.assert_called_once()
            mock_session.commit.assert_called_once()
            assert resultado is True

    def test_listar_por_usuario_periodo(self):
        """Lista planejamentos do usuário."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            plans = [Mock(spec=AgendaPrevistaAdmin), Mock(spec=AgendaPrevistaAdmin)]
            mock_session.execute.return_value.scalars.return_value.all.return_value = plans

            from src.cp.repositories.capacidade.repositories import AgendaPrevistaRepository
            repo = AgendaPrevistaRepository(MagicMock())
            resultado = repo.listar_por_usuario_periodo(2, date(2026, 3, 1), date(2026, 3, 31))

            assert len(resultado) == 2


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO AGENDA LANCAMENTO REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════


class TestAgendaLancamentoRepository:
    """Testes do AgendaLancamentoRepository."""

    def test_criar(self):
        """Cria novo lançamento."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)

            from src.cp.repositories.capacidade.repositories import AgendaLancamentoRepository
            repo = AgendaLancamentoRepository(MagicMock())
            
            repo.criar(
                usuario_id=2,
                data=date(2026, 3, 10),
                bloco_id=1,
                tipo_atividade_id=1,
                faixa=FaixaMinuto.NORMAL,
                minutos=120,
                descricao=None,
                criado_por=2,
            )

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_buscar_por_id(self):
        """Busca lançamento por ID."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            lanc = Mock(spec=AgendaLancamento)
            lanc.id = 1
            mock_session.get.return_value = lanc

            from src.cp.repositories.capacidade.repositories import AgendaLancamentoRepository
            repo = AgendaLancamentoRepository(MagicMock())
            resultado = repo.buscar_por_id(1)

            assert resultado == lanc

    def test_soma_minutos_dia(self):
        """Soma minutos do dia."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = 240

            from src.cp.repositories.capacidade.repositories import AgendaLancamentoRepository
            repo = AgendaLancamentoRepository(MagicMock())
            resultado = repo.soma_minutos_dia(2, date(2026, 3, 10), FaixaMinuto.NORMAL)

            assert resultado == 240

    def test_soma_minutos_dia_none(self):
        """Retorna 0 se None."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = None

            from src.cp.repositories.capacidade.repositories import AgendaLancamentoRepository
            repo = AgendaLancamentoRepository(MagicMock())
            resultado = repo.soma_minutos_dia(2, date(2026, 3, 10), FaixaMinuto.NORMAL)

            assert resultado == 0

    def test_atualizar(self):
        """Atualiza lançamento."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            lanc = Mock(spec=AgendaLancamento)
            lanc.id = 1
            mock_session.get.return_value = lanc

            from src.cp.repositories.capacidade.repositories import AgendaLancamentoRepository
            repo = AgendaLancamentoRepository(MagicMock())
            repo.atualizar(id=1, minutos=150, descricao=None, atualizado_por=2)

            mock_session.commit.assert_called_once()

    def test_remover(self):
        """Remove lançamento."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            lanc = Mock(spec=AgendaLancamento)
            mock_session.get.return_value = lanc

            from src.cp.repositories.capacidade.repositories import AgendaLancamentoRepository
            repo = AgendaLancamentoRepository(MagicMock())
            resultado = repo.remover(1)

            mock_session.delete.assert_called_once()
            assert resultado is True

    def test_listar_por_usuario_periodo(self):
        """Lista lançamentos do usuário."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            lancs = [Mock(spec=AgendaLancamento), Mock(spec=AgendaLancamento)]
            mock_session.execute.return_value.scalars.return_value.all.return_value = lancs

            from src.cp.repositories.capacidade.repositories import AgendaLancamentoRepository
            repo = AgendaLancamentoRepository(MagicMock())
            resultado = repo.listar_por_usuario_periodo(2, date(2026, 3, 1), date(2026, 3, 31))

            assert len(resultado) == 2

    def test_listar_por_dia(self):
        """Lista lançamentos do dia."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            lancs = [Mock(spec=AgendaLancamento)]
            mock_session.execute.return_value.scalars.return_value.all.return_value = lancs

            from src.cp.repositories.capacidade.repositories import AgendaLancamentoRepository
            repo = AgendaLancamentoRepository(MagicMock())
            resultado = repo.listar_por_dia(2, date(2026, 3, 10))

            assert len(resultado) == 1


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO FERIADO REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════


class TestFeriadoRepository:
    """Testes do FeriadoRepository."""

    def test_criar(self):
        """Cria novo feriado."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)

            from src.cp.repositories.capacidade.repositories import FeriadoRepository
            repo = FeriadoRepository(MagicMock())
            
            repo.criar(date(2026, 4, 21), "Tiradentes", 1)

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_buscar_por_data(self):
        """Busca feriado por data."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            feriado = Mock(spec=Feriado)
            mock_session.execute.return_value.scalar_one_or_none.return_value = feriado

            from src.cp.repositories.capacidade.repositories import FeriadoRepository
            repo = FeriadoRepository(MagicMock())
            resultado = repo.buscar_por_data(date(2026, 4, 21))

            assert resultado == feriado

    def test_eh_feriado_true(self):
        """Retorna True se é feriado."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = Mock()

            from src.cp.repositories.capacidade.repositories import FeriadoRepository
            repo = FeriadoRepository(MagicMock())
            resultado = repo.eh_feriado(date(2026, 4, 21))

            assert resultado is True

    def test_eh_feriado_false(self):
        """Retorna False se não é feriado."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = None

            from src.cp.repositories.capacidade.repositories import FeriadoRepository
            repo = FeriadoRepository(MagicMock())
            resultado = repo.eh_feriado(date(2026, 3, 10))

            assert resultado is False

    def test_listar_todos(self):
        """Lista todos os feriados."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            feriados = [Mock(spec=Feriado), Mock(spec=Feriado)]
            mock_session.execute.return_value.scalars.return_value.all.return_value = feriados

            from src.cp.repositories.capacidade.repositories import FeriadoRepository
            repo = FeriadoRepository(MagicMock())
            resultado = repo.listar_todos()

            assert len(resultado) == 2

    def test_remover(self):
        """Remove feriado."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            feriado = Mock(spec=Feriado)
            mock_session.get.return_value = feriado

            from src.cp.repositories.capacidade.repositories import FeriadoRepository
            repo = FeriadoRepository(MagicMock())
            resultado = repo.remover(1)

            mock_session.delete.assert_called_once()
            assert resultado is True


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO INDISPONIBILIDADE REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════


class TestIndisponibilidadeRepository:
    """Testes do IndisponibilidadeRepository."""

    def test_criar(self):
        """Cria nova indisponibilidade."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)

            from src.cp.repositories.capacidade.repositories import IndisponibilidadeRepository
            repo = IndisponibilidadeRepository(MagicMock())
            
            repo.criar(
                usuario_id=2,
                tipo_atividade_id=4,
                data_inicio=date(2026, 7, 1),
                data_fim=date(2026, 7, 15),
                descricao="Férias",
                criado_por=1,
            )

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_verificar_sobreposicao_true(self):
        """Retorna True se há sobreposição."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = Mock()

            from src.cp.repositories.capacidade.repositories import IndisponibilidadeRepository
            repo = IndisponibilidadeRepository(MagicMock())
            resultado = repo.verificar_sobreposicao(2, date(2026, 7, 1), date(2026, 7, 15))

            assert resultado is True

    def test_verificar_sobreposicao_false(self):
        """Retorna False se não há sobreposição."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            mock_session.execute.return_value.scalar_one_or_none.return_value = None

            from src.cp.repositories.capacidade.repositories import IndisponibilidadeRepository
            repo = IndisponibilidadeRepository(MagicMock())
            resultado = repo.verificar_sobreposicao(2, date(2026, 7, 1), date(2026, 7, 15))

            assert resultado is False

    def test_buscar_para_data(self):
        """Busca indisponibilidade para data."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            indisp = Mock(spec=IndisponibilidadeUsuario)
            mock_session.execute.return_value.scalar_one_or_none.return_value = indisp

            from src.cp.repositories.capacidade.repositories import IndisponibilidadeRepository
            repo = IndisponibilidadeRepository(MagicMock())
            resultado = repo.buscar_para_data(2, date(2026, 7, 10))

            assert resultado == indisp

    def test_listar_por_usuario(self):
        """Lista indisponibilidades do usuário."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            indisps = [Mock(spec=IndisponibilidadeUsuario)]
            mock_session.execute.return_value.scalars.return_value.all.return_value = indisps

            from src.cp.repositories.capacidade.repositories import IndisponibilidadeRepository
            repo = IndisponibilidadeRepository(MagicMock())
            resultado = repo.listar_por_usuario(2)

            assert len(resultado) == 1

    def test_remover(self):
        """Remove indisponibilidade."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            indisp = Mock(spec=IndisponibilidadeUsuario)
            mock_session.get.return_value = indisp

            from src.cp.repositories.capacidade.repositories import IndisponibilidadeRepository
            repo = IndisponibilidadeRepository(MagicMock())
            resultado = repo.remover(1)

            mock_session.delete.assert_called_once()
            assert resultado is True


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO AUDIT LOG REPOSITORY
# ══════════════════════════════════════════════════════════════════════════════


class TestAuditLogRepository:
    """Testes do AuditLogRepository."""

    def test_registrar(self):
        """Registra log de auditoria."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)

            from src.cp.repositories.capacidade.repositories import AuditLogRepository
            repo = AuditLogRepository(MagicMock())
            
            repo.registrar(
                entidade="teste",
                entidade_id=1,
                acao=AcaoAuditoria.CREATE,
                antes=None,
                depois={"id": 1},
                usuario_executor=1,
            )

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_listar_por_entidade(self):
        """Lista logs por entidade."""
        with patch("src.cp.repositories.capacidade.repositories.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_session)
            MockSession.return_value.__exit__ = Mock(return_value=None)
            
            logs = [Mock(spec=AuditLog), Mock(spec=AuditLog)]
            mock_session.execute.return_value.scalars.return_value.all.return_value = logs

            from src.cp.repositories.capacidade.repositories import AuditLogRepository
            repo = AuditLogRepository(MagicMock())
            resultado = repo.listar_por_entidade("teste", 1)

            assert len(resultado) == 2
