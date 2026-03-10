"""Testes completos dos serviços de Capacidade.

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
    CapacidadeDia,
    Feriado,
    IndisponibilidadeUsuario,
    ParametroCapacidade,
    TipoAtividade,
)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS PARA CRIAR MOCKS
# ══════════════════════════════════════════════════════════════════════════════


def mock_parametro(
    id: int = 1,
    minutos_dia: int = 360,
    minutos_extra: int = 240,
    data_inicio: date = date(2026, 1, 1),
    data_fim: date | None = None,
) -> Mock:
    """Cria mock de ParametroCapacidade."""
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
    """Cria mock de CapacidadeDia."""
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
    nome: str = "Trabalho em Bloco",
    grupo: GrupoAtividade = GrupoAtividade.PRODUCAO,
) -> Mock:
    """Cria mock de TipoAtividade."""
    m = Mock(spec=TipoAtividade)
    m.id = id
    m.codigo = codigo
    m.nome = nome
    m.grupo = grupo
    return m


def mock_lancamento(
    id: int = 1,
    usuario_id: int = 2,
    data: date = date(2026, 3, 10),
    bloco_id: int | None = 1,
    tipo_atividade_id: int = 1,
    faixa: FaixaMinuto = FaixaMinuto.NORMAL,
    minutos: int = 120,
    codigo: CodigoAtividade = CodigoAtividade.BLOCO,
) -> Mock:
    """Cria mock de AgendaLancamento."""
    m = Mock(spec=AgendaLancamento)
    m.id = id
    m.usuario_id = usuario_id
    m.data_lancamento = data
    m.bloco_id = bloco_id
    m.tipo_atividade_id = tipo_atividade_id
    m.faixa_minuto = faixa
    m.minutos = minutos
    m.descricao = None
    m.criado_por = usuario_id
    m.atualizado_por = None
    m.criado_em = datetime.now()
    m.atualizado_em = datetime.now()
    m.tipo_atividade = mock_tipo_atividade(id=tipo_atividade_id, codigo=codigo)
    return m


def mock_planejamento(
    id: int = 1,
    usuario_id: int = 2,
    data: date = date(2026, 3, 10),
    bloco_id: int | None = 1,
    minutos_normais: int = 120,
    minutos_extras: int = 0,
) -> Mock:
    """Cria mock de AgendaPrevistaAdmin."""
    m = Mock(spec=AgendaPrevistaAdmin)
    m.id = id
    m.usuario_id = usuario_id
    m.data = data
    m.bloco_id = bloco_id
    m.minutos_planejados_normais = minutos_normais
    m.minutos_planejados_extras = minutos_extras
    m.descricao = None
    m.criado_por = 1
    m.criado_em = datetime.now()
    m.atualizado_em = datetime.now()
    return m


def mock_feriado(
    id: int = 1,
    data: date = date(2026, 4, 21),
    descricao: str = "Tiradentes",
) -> Mock:
    """Cria mock de Feriado."""
    m = Mock(spec=Feriado)
    m.id = id
    m.data = data
    m.descricao = descricao
    m.criado_por = 1
    m.criado_em = datetime.now()
    return m


def mock_indisponibilidade(
    id: int = 1,
    usuario_id: int = 2,
    tipo_atividade_id: int = 4,
    data_inicio: date = date(2026, 7, 1),
    data_fim: date = date(2026, 7, 15),
) -> Mock:
    """Cria mock de IndisponibilidadeUsuario."""
    m = Mock(spec=IndisponibilidadeUsuario)
    m.id = id
    m.usuario_id = usuario_id
    m.tipo_atividade_id = tipo_atividade_id
    m.data_inicio = data_inicio
    m.data_fim = data_fim
    m.descricao = "Férias"
    m.criado_por = 1
    m.criado_em = datetime.now()
    return m


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO AGENDA SERVICE
# ══════════════════════════════════════════════════════════════════════════════


class TestAgendaServiceValidacoes:
    """Testes das validações do AgendaService."""

    @pytest.fixture
    def service(self):
        """Cria AgendaService com mocks."""
        with patch("cp.services.capacidade.agenda_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.agenda_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.agenda_service.FeriadoRepository"), \
             patch("cp.services.capacidade.agenda_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.agenda_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeService"), \
             patch("cp.services.capacidade.agenda_service.AuditService"):
            
            from cp.services.capacidade.agenda_service import AgendaService
            svc = AgendaService(MagicMock())
            return svc

    # ── _validar_data_operador ────────────────────────────────────────────────

    def test_validar_data_operador_passada_ok(self, service):
        """Data passada é válida."""
        service._validar_data_operador(date(2026, 3, 5), date(2026, 3, 10))

    def test_validar_data_operador_atual_ok(self, service):
        """Data atual é válida."""
        service._validar_data_operador(date(2026, 3, 10), date(2026, 3, 10))

    def test_validar_data_operador_futura_erro(self, service):
        """Data futura lança exceção."""
        with pytest.raises(DataFuturaError) as exc_info:
            service._validar_data_operador(date(2026, 3, 15), date(2026, 3, 10))
        assert exc_info.value.data_lancamento == date(2026, 3, 15)
        assert exc_info.value.data_atual == date(2026, 3, 10)

    # ── _validar_dia_aberto ───────────────────────────────────────────────────

    def test_validar_dia_aberto_sem_capacidade_ok(self, service):
        """Dia sem capacidade materializada é considerado aberto."""
        service._capacidade_repo.buscar.return_value = None
        service._validar_dia_aberto(2, date(2026, 3, 10), FaixaMinuto.NORMAL, False)

    def test_validar_dia_aberto_status_aberto_ok(self, service):
        """Dia com status ABERTO permite alteração."""
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia(status=StatusDia.ABERTO)
        service._validar_dia_aberto(2, date(2026, 3, 10), FaixaMinuto.NORMAL, False)

    def test_validar_dia_consolidado_operador_normal_erro(self, service):
        """Operador não pode alterar normal em dia consolidado."""
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia(status=StatusDia.CONSOLIDADO)
        with pytest.raises(DiaConsolidadoError) as exc_info:
            service._validar_dia_aberto(2, date(2026, 3, 10), FaixaMinuto.NORMAL, eh_admin=False)
        assert exc_info.value.permite_extra is True

    def test_validar_dia_consolidado_operador_extra_ok(self, service):
        """Operador pode lançar extra em dia consolidado."""
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia(status=StatusDia.CONSOLIDADO)
        service._validar_dia_aberto(2, date(2026, 3, 10), FaixaMinuto.EXTRA, eh_admin=False)

    def test_validar_dia_consolidado_admin_normal_ok(self, service):
        """Admin pode alterar normal em dia consolidado."""
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia(status=StatusDia.CONSOLIDADO)
        service._validar_dia_aberto(2, date(2026, 3, 10), FaixaMinuto.NORMAL, eh_admin=True)

    # ── _validar_capacidade_normal ────────────────────────────────────────────

    def test_validar_capacidade_normal_dentro_limite_ok(self, service):
        """Minutos dentro do limite passam."""
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia(minutos_normal=360)
        service._lancamento_repo.soma_minutos_dia.return_value = 200
        service._validar_capacidade_normal(2, date(2026, 3, 10), 100)

    def test_validar_capacidade_normal_materializa_se_necessario(self, service):
        """Se não há capacidade, materializa."""
        service._capacidade_repo.buscar.return_value = None
        service._capacidade_service.materializar_capacidade_dia.return_value = mock_capacidade_dia()
        service._lancamento_repo.soma_minutos_dia.return_value = 0
        
        service._validar_capacidade_normal(2, date(2026, 3, 10), 100)
        service._capacidade_service.materializar_capacidade_dia.assert_called_once()

    def test_validar_capacidade_normal_dia_indisponivel_erro(self, service):
        """Dia indisponível lança erro."""
        cap = mock_capacidade_dia(eh_indisponivel=True, tipo_indisponibilidade=TipoIndisponibilidade.FERIAS)
        service._capacidade_repo.buscar.return_value = cap
        
        with pytest.raises(DiaIndisponivelError) as exc_info:
            service._validar_capacidade_normal(2, date(2026, 7, 10), 100)
        assert exc_info.value.tipo == "FERIAS"

    def test_validar_capacidade_normal_dia_indisponivel_sem_tipo(self, service):
        """Dia indisponível sem tipo usa texto padrão."""
        cap = mock_capacidade_dia(eh_indisponivel=True, tipo_indisponibilidade=None)
        service._capacidade_repo.buscar.return_value = cap
        
        with pytest.raises(DiaIndisponivelError) as exc_info:
            service._validar_capacidade_normal(2, date(2026, 7, 10), 100)
        assert exc_info.value.tipo == "indisponível"

    def test_validar_capacidade_normal_excede_erro(self, service):
        """Exceder capacidade lança erro."""
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia(minutos_normal=360)
        service._lancamento_repo.soma_minutos_dia.return_value = 300
        
        with pytest.raises(LimiteCapacidadeExcedidoError) as exc_info:
            service._validar_capacidade_normal(2, date(2026, 3, 10), 100)  # 300 + 100 > 360
        assert exc_info.value.capacidade_disponivel == 60
        assert exc_info.value.minutos_solicitados == 100

    def test_validar_capacidade_normal_desconta_edicao(self, service):
        """Ao editar, desconta minutos do lançamento atual."""
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia(minutos_normal=360)
        service._lancamento_repo.soma_minutos_dia.return_value = 360
        service._lancamento_repo.buscar_por_id.return_value = mock_lancamento(minutos=60)
        
        # Com edição: 360 - 60 = 300 disponível, solicitando 50 = OK
        service._validar_capacidade_normal(2, date(2026, 3, 10), 50, excluir_lancamento_id=1)

    def test_validar_capacidade_normal_desconta_edicao_faixa_extra(self, service):
        """Ao editar lançamento extra, não desconta."""
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia(minutos_normal=360)
        service._lancamento_repo.soma_minutos_dia.return_value = 350
        service._lancamento_repo.buscar_por_id.return_value = mock_lancamento(minutos=60, faixa=FaixaMinuto.EXTRA)
        
        # Lançamento é EXTRA, não desconta do normal
        with pytest.raises(LimiteCapacidadeExcedidoError):
            service._validar_capacidade_normal(2, date(2026, 3, 10), 50, excluir_lancamento_id=1)

    # ── _validar_proprietario_lancamento ──────────────────────────────────────

    def test_validar_proprietario_proprio_ok(self, service):
        """Usuário pode editar próprio lançamento."""
        lanc = mock_lancamento(usuario_id=2)
        service._validar_proprietario_lancamento(lanc, usuario_id=2, eh_admin=False)

    def test_validar_proprietario_outro_erro(self, service):
        """Usuário não pode editar lançamento de outro."""
        lanc = mock_lancamento(usuario_id=3)
        with pytest.raises(AcessoNegadoError):
            service._validar_proprietario_lancamento(lanc, usuario_id=2, eh_admin=False)

    def test_validar_proprietario_admin_ok(self, service):
        """Admin pode editar qualquer lançamento."""
        lanc = mock_lancamento(usuario_id=3)
        service._validar_proprietario_lancamento(lanc, usuario_id=1, eh_admin=True)


class TestAgendaServicePlanejamento:
    """Testes das operações de planejamento."""

    @pytest.fixture
    def service(self):
        """Cria AgendaService com mocks."""
        with patch("cp.services.capacidade.agenda_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.agenda_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.agenda_service.FeriadoRepository"), \
             patch("cp.services.capacidade.agenda_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.agenda_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeService"), \
             patch("cp.services.capacidade.agenda_service.AuditService"):
            
            from cp.services.capacidade.agenda_service import AgendaService
            return AgendaService(MagicMock())

    def test_criar_planejamento_novo(self, service):
        """Cria novo planejamento."""
        plan = mock_planejamento()
        service._planejamento_repo.buscar_existente.return_value = None
        service._planejamento_repo.criar.return_value = plan

        resultado = service.criar_planejamento(
            usuario_id=2, data=date(2026, 3, 10), bloco_id=1,
            minutos_normais=120, minutos_extras=0,
            descricao=None, criado_por=1
        )

        assert resultado == plan
        service._planejamento_repo.criar.assert_called_once()
        service._audit.auditar_planejamento_criado.assert_called_once()

    def test_criar_planejamento_existente_atualiza(self, service):
        """Se já existe, atualiza ao invés de criar."""
        existente = mock_planejamento(id=1)
        atualizado = mock_planejamento(id=1, minutos_normais=180)
        
        service._planejamento_repo.buscar_existente.return_value = existente
        service._planejamento_repo.buscar_por_id.return_value = existente
        service._planejamento_repo.atualizar.return_value = atualizado

        resultado = service.criar_planejamento(
            usuario_id=2, data=date(2026, 3, 10), bloco_id=1,
            minutos_normais=180, minutos_extras=0,
            descricao=None, criado_por=1
        )

        assert resultado.minutos_planejados_normais == 180
        service._planejamento_repo.criar.assert_not_called()

    def test_atualizar_planejamento_sucesso(self, service):
        """Atualiza planejamento existente."""
        antes = mock_planejamento(id=1, minutos_normais=120)
        depois = mock_planejamento(id=1, minutos_normais=180)
        
        service._planejamento_repo.buscar_por_id.return_value = antes
        service._planejamento_repo.atualizar.return_value = depois

        resultado = service.atualizar_planejamento(
            id=1, minutos_normais=180, minutos_extras=None,
            descricao=None, atualizado_por=1
        )

        assert resultado == depois
        service._audit.auditar_planejamento_atualizado.assert_called_once()

    def test_atualizar_planejamento_nao_encontrado(self, service):
        """Erro se planejamento não existe."""
        service._planejamento_repo.buscar_por_id.return_value = None

        with pytest.raises(RegistroNaoEncontradoError):
            service.atualizar_planejamento(
                id=999, minutos_normais=180, minutos_extras=None,
                descricao=None, atualizado_por=1
            )

    def test_remover_planejamento_sucesso(self, service):
        """Remove planejamento existente."""
        plan = mock_planejamento(id=1)
        service._planejamento_repo.buscar_por_id.return_value = plan
        service._planejamento_repo.remover.return_value = True

        resultado = service.remover_planejamento(id=1, removido_por=1)

        assert resultado is True
        service._audit.auditar_planejamento_removido.assert_called_once()

    def test_remover_planejamento_nao_encontrado(self, service):
        """Erro se planejamento não existe."""
        service._planejamento_repo.buscar_por_id.return_value = None

        with pytest.raises(RegistroNaoEncontradoError):
            service.remover_planejamento(id=999, removido_por=1)

    def test_listar_planejamento_usuario(self, service):
        """Lista planejamentos do usuário."""
        plans = [mock_planejamento(id=1), mock_planejamento(id=2)]
        service._planejamento_repo.listar_por_usuario_periodo.return_value = plans

        resultado = service.listar_planejamento_usuario(2, date(2026, 3, 1), date(2026, 3, 31))

        assert len(resultado) == 2

    def test_listar_planejamento_geral(self, service):
        """Lista todos os planejamentos."""
        plans = [mock_planejamento(id=1), mock_planejamento(id=2)]
        service._planejamento_repo.listar_todos_periodo.return_value = plans

        resultado = service.listar_planejamento_geral(date(2026, 3, 1), date(2026, 3, 31))

        assert len(resultado) == 2


class TestAgendaServiceLancamentos:
    """Testes das operações de lançamento."""

    @pytest.fixture
    def service(self):
        """Cria AgendaService com mocks."""
        with patch("cp.services.capacidade.agenda_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.agenda_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.agenda_service.FeriadoRepository"), \
             patch("cp.services.capacidade.agenda_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.agenda_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeService"), \
             patch("cp.services.capacidade.agenda_service.AuditService"):
            
            from cp.services.capacidade.agenda_service import AgendaService
            return AgendaService(MagicMock())

    def test_criar_lancamento_operador_sucesso(self, service):
        """Operador cria lançamento em data válida."""
        lanc = mock_lancamento()
        tipo = mock_tipo_atividade()
        
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia()
        service._lancamento_repo.soma_minutos_dia.return_value = 0
        service._tipo_atividade_repo.buscar_por_codigo.return_value = tipo
        service._lancamento_repo.criar.return_value = lanc

        resultado, alertas = service.criar_lancamento(
            usuario_id=2, data=date(2026, 3, 10), bloco_id=1,
            tipo_atividade=CodigoAtividade.BLOCO, faixa=FaixaMinuto.NORMAL,
            minutos=120, descricao=None, criado_por=2,
            eh_admin=False, data_atual=date(2026, 3, 10)
        )

        assert resultado == lanc
        assert alertas == []

    def test_criar_lancamento_operador_data_futura_erro(self, service):
        """Operador não pode lançar em data futura."""
        with pytest.raises(DataFuturaError):
            service.criar_lancamento(
                usuario_id=2, data=date(2026, 3, 15), bloco_id=1,
                tipo_atividade=CodigoAtividade.BLOCO, faixa=FaixaMinuto.NORMAL,
                minutos=120, descricao=None, criado_por=2,
                eh_admin=False, data_atual=date(2026, 3, 10)
            )

    def test_criar_lancamento_admin_data_futura_ok(self, service):
        """Admin pode lançar em data futura."""
        lanc = mock_lancamento()
        tipo = mock_tipo_atividade()
        
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia()
        service._lancamento_repo.soma_minutos_dia.return_value = 0
        service._tipo_atividade_repo.buscar_por_codigo.return_value = tipo
        service._lancamento_repo.criar.return_value = lanc

        resultado, alertas = service.criar_lancamento(
            usuario_id=2, data=date(2026, 3, 15), bloco_id=1,
            tipo_atividade=CodigoAtividade.BLOCO, faixa=FaixaMinuto.NORMAL,
            minutos=120, descricao=None, criado_por=1,
            eh_admin=True, data_atual=date(2026, 3, 10)
        )

        assert resultado == lanc

    def test_criar_lancamento_tipo_nao_encontrado_erro(self, service):
        """Erro se tipo de atividade não existe."""
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia()
        service._lancamento_repo.soma_minutos_dia.return_value = 0
        service._tipo_atividade_repo.buscar_por_codigo.return_value = None

        with pytest.raises(RegistroNaoEncontradoError):
            service.criar_lancamento(
                usuario_id=2, data=date(2026, 3, 10), bloco_id=1,
                tipo_atividade=CodigoAtividade.BLOCO, faixa=FaixaMinuto.NORMAL,
                minutos=120, descricao=None, criado_por=2,
                eh_admin=False, data_atual=date(2026, 3, 10)
            )

    def test_criar_lancamento_dia_consolidado_gera_alerta(self, service):
        """Lançamento em dia consolidado gera alerta."""
        lanc = mock_lancamento()
        tipo = mock_tipo_atividade()
        cap = mock_capacidade_dia(status=StatusDia.CONSOLIDADO)
        
        # Admin pode lançar em consolidado
        service._capacidade_repo.buscar.return_value = cap
        service._lancamento_repo.soma_minutos_dia.return_value = 0
        service._tipo_atividade_repo.buscar_por_codigo.return_value = tipo
        service._lancamento_repo.criar.return_value = lanc

        resultado, alertas = service.criar_lancamento(
            usuario_id=2, data=date(2026, 3, 10), bloco_id=1,
            tipo_atividade=CodigoAtividade.BLOCO, faixa=FaixaMinuto.NORMAL,
            minutos=120, descricao=None, criado_por=1,
            eh_admin=True, data_atual=date(2026, 3, 10)
        )

        assert len(alertas) == 1
        assert "consolidado" in alertas[0].lower()

    def test_atualizar_lancamento_sucesso(self, service):
        """Atualiza lançamento existente."""
        antes = mock_lancamento(id=1, minutos=120)
        depois = mock_lancamento(id=1, minutos=150)
        
        service._lancamento_repo.buscar_por_id.return_value = antes
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia()
        service._lancamento_repo.soma_minutos_dia.return_value = 120
        service._lancamento_repo.atualizar.return_value = depois

        resultado, alertas = service.atualizar_lancamento(
            id=1, minutos=150, descricao=None, atualizado_por=2, eh_admin=False
        )

        assert resultado == depois

    def test_atualizar_lancamento_nao_encontrado(self, service):
        """Erro se lançamento não existe."""
        service._lancamento_repo.buscar_por_id.return_value = None

        with pytest.raises(RegistroNaoEncontradoError):
            service.atualizar_lancamento(
                id=999, minutos=150, descricao=None, atualizado_por=2, eh_admin=False
            )

    def test_atualizar_lancamento_outro_usuario_erro(self, service):
        """Operador não pode atualizar lançamento de outro."""
        antes = mock_lancamento(id=1, usuario_id=3)
        service._lancamento_repo.buscar_por_id.return_value = antes

        with pytest.raises(AcessoNegadoError):
            service.atualizar_lancamento(
                id=1, minutos=150, descricao=None, atualizado_por=2, eh_admin=False
            )

    def test_remover_lancamento_sucesso(self, service):
        """Remove lançamento existente."""
        lanc = mock_lancamento(id=1)
        service._lancamento_repo.buscar_por_id.return_value = lanc
        service._capacidade_repo.buscar.return_value = mock_capacidade_dia()
        service._lancamento_repo.remover.return_value = True

        resultado = service.remover_lancamento(id=1, removido_por=2, eh_admin=False)

        assert resultado is True

    def test_remover_lancamento_nao_encontrado(self, service):
        """Erro se lançamento não existe."""
        service._lancamento_repo.buscar_por_id.return_value = None

        with pytest.raises(RegistroNaoEncontradoError):
            service.remover_lancamento(id=999, removido_por=2, eh_admin=False)


class TestAgendaServiceFeriados:
    """Testes das operações de feriados."""

    @pytest.fixture
    def service(self):
        """Cria AgendaService com mocks."""
        with patch("cp.services.capacidade.agenda_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.agenda_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.agenda_service.FeriadoRepository"), \
             patch("cp.services.capacidade.agenda_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.agenda_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeService"), \
             patch("cp.services.capacidade.agenda_service.AuditService"):
            
            from cp.services.capacidade.agenda_service import AgendaService
            return AgendaService(MagicMock())

    def test_criar_feriado_sucesso(self, service):
        """Cria novo feriado."""
        feriado = mock_feriado()
        service._feriado_repo.buscar_por_data.return_value = None
        service._feriado_repo.criar.return_value = feriado

        resultado = service.criar_feriado(
            data=date(2026, 4, 21), descricao="Tiradentes", criado_por=1
        )

        assert resultado == feriado
        service._audit.auditar_feriado_criado.assert_called_once()

    def test_criar_feriado_duplicado_erro(self, service):
        """Erro se feriado já existe."""
        service._feriado_repo.buscar_por_data.return_value = mock_feriado()

        with pytest.raises(FeriadoDuplicadoError):
            service.criar_feriado(
                data=date(2026, 4, 21), descricao="Tiradentes", criado_por=1
            )

    def test_remover_feriado_sucesso(self, service):
        """Remove feriado existente."""
        feriado = mock_feriado(id=1)
        service._feriado_repo.buscar_por_id.return_value = feriado
        service._feriado_repo.remover.return_value = True

        resultado = service.remover_feriado(id=1, removido_por=1)

        assert resultado is True
        service._audit.auditar_feriado_removido.assert_called_once()

    def test_remover_feriado_nao_encontrado(self, service):
        """Erro se feriado não existe."""
        service._feriado_repo.buscar_por_id.return_value = None

        with pytest.raises(RegistroNaoEncontradoError):
            service.remover_feriado(id=999, removido_por=1)

    def test_listar_feriados(self, service):
        """Lista todos os feriados."""
        feriados = [mock_feriado(id=1), mock_feriado(id=2)]
        service._feriado_repo.listar_todos.return_value = feriados

        resultado = service.listar_feriados()

        assert len(resultado) == 2

    def test_listar_feriados_periodo(self, service):
        """Lista feriados do período."""
        feriados = [mock_feriado(id=1)]
        service._feriado_repo.listar_periodo.return_value = feriados

        resultado = service.listar_feriados_periodo(date(2026, 4, 1), date(2026, 4, 30))

        assert len(resultado) == 1


class TestAgendaServiceIndisponibilidades:
    """Testes das operações de indisponibilidades."""

    @pytest.fixture
    def service(self):
        """Cria AgendaService com mocks."""
        with patch("cp.services.capacidade.agenda_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.agenda_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.agenda_service.FeriadoRepository"), \
             patch("cp.services.capacidade.agenda_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.agenda_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeService"), \
             patch("cp.services.capacidade.agenda_service.AuditService"):
            
            from cp.services.capacidade.agenda_service import AgendaService
            return AgendaService(MagicMock())

    def test_criar_indisponibilidade_ferias(self, service):
        """Cria indisponibilidade de férias."""
        indisp = mock_indisponibilidade()
        tipo = mock_tipo_atividade(codigo=CodigoAtividade.FERIAS)
        
        service._indisponibilidade_repo.verificar_sobreposicao.return_value = False
        service._tipo_atividade_repo.buscar_por_codigo.return_value = tipo
        service._indisponibilidade_repo.criar.return_value = indisp

        resultado = service.criar_indisponibilidade(
            usuario_id=2, tipo=TipoIndisponibilidade.FERIAS,
            data_inicio=date(2026, 7, 1), data_fim=date(2026, 7, 15),
            descricao="Férias", criado_por=1
        )

        assert resultado == indisp
        service._audit.auditar_indisponibilidade_criada.assert_called_once()

    def test_criar_indisponibilidade_licenca(self, service):
        """Cria indisponibilidade de licença."""
        indisp = mock_indisponibilidade()
        tipo = mock_tipo_atividade(codigo=CodigoAtividade.LICENCA)
        
        service._indisponibilidade_repo.verificar_sobreposicao.return_value = False
        service._tipo_atividade_repo.buscar_por_codigo.return_value = tipo
        service._indisponibilidade_repo.criar.return_value = indisp

        resultado = service.criar_indisponibilidade(
            usuario_id=2, tipo=TipoIndisponibilidade.LICENCA,
            data_inicio=date(2026, 7, 1), data_fim=date(2026, 7, 15),
            descricao=None, criado_por=1
        )

        assert resultado == indisp

    def test_criar_indisponibilidade_curso(self, service):
        """Cria indisponibilidade de curso."""
        indisp = mock_indisponibilidade()
        tipo = mock_tipo_atividade(codigo=CodigoAtividade.CURSO)
        
        service._indisponibilidade_repo.verificar_sobreposicao.return_value = False
        service._tipo_atividade_repo.buscar_por_codigo.return_value = tipo
        service._indisponibilidade_repo.criar.return_value = indisp

        resultado = service.criar_indisponibilidade(
            usuario_id=2, tipo=TipoIndisponibilidade.CURSO,
            data_inicio=date(2026, 7, 1), data_fim=date(2026, 7, 15),
            descricao=None, criado_por=1
        )

        assert resultado == indisp

    def test_criar_indisponibilidade_afastamento(self, service):
        """Cria indisponibilidade de afastamento."""
        indisp = mock_indisponibilidade()
        tipo = mock_tipo_atividade(codigo=CodigoAtividade.AFASTAMENTO)
        
        service._indisponibilidade_repo.verificar_sobreposicao.return_value = False
        service._tipo_atividade_repo.buscar_por_codigo.return_value = tipo
        service._indisponibilidade_repo.criar.return_value = indisp

        resultado = service.criar_indisponibilidade(
            usuario_id=2, tipo=TipoIndisponibilidade.AFASTAMENTO,
            data_inicio=date(2026, 7, 1), data_fim=date(2026, 7, 15),
            descricao=None, criado_por=1
        )

        assert resultado == indisp

    def test_criar_indisponibilidade_intervalo_invalido(self, service):
        """Erro se data_fim < data_inicio."""
        with pytest.raises(IntervaloInvalidoError):
            service.criar_indisponibilidade(
                usuario_id=2, tipo=TipoIndisponibilidade.FERIAS,
                data_inicio=date(2026, 7, 15), data_fim=date(2026, 7, 1),
                descricao=None, criado_por=1
            )

    def test_criar_indisponibilidade_sobreposta(self, service):
        """Erro se há sobreposição."""
        service._indisponibilidade_repo.verificar_sobreposicao.return_value = True

        with pytest.raises(IndisponibilidadeSobrepostaError):
            service.criar_indisponibilidade(
                usuario_id=2, tipo=TipoIndisponibilidade.FERIAS,
                data_inicio=date(2026, 7, 1), data_fim=date(2026, 7, 15),
                descricao=None, criado_por=1
            )

    def test_criar_indisponibilidade_tipo_nao_encontrado(self, service):
        """Erro se tipo de atividade não existe."""
        service._indisponibilidade_repo.verificar_sobreposicao.return_value = False
        service._tipo_atividade_repo.buscar_por_codigo.return_value = None

        with pytest.raises(RegistroNaoEncontradoError):
            service.criar_indisponibilidade(
                usuario_id=2, tipo=TipoIndisponibilidade.FERIAS,
                data_inicio=date(2026, 7, 1), data_fim=date(2026, 7, 15),
                descricao=None, criado_por=1
            )

    def test_remover_indisponibilidade_sucesso(self, service):
        """Remove indisponibilidade existente."""
        indisp = mock_indisponibilidade(id=1)
        service._indisponibilidade_repo.buscar_por_id.return_value = indisp
        service._indisponibilidade_repo.remover.return_value = True

        resultado = service.remover_indisponibilidade(id=1, removido_por=1)

        assert resultado is True

    def test_remover_indisponibilidade_nao_encontrada(self, service):
        """Erro se indisponibilidade não existe."""
        service._indisponibilidade_repo.buscar_por_id.return_value = None

        with pytest.raises(RegistroNaoEncontradoError):
            service.remover_indisponibilidade(id=999, removido_por=1)


class TestAgendaServiceAgendaCompleta:
    """Testes da montagem da agenda completa."""

    @pytest.fixture
    def service(self):
        """Cria AgendaService com mocks."""
        with patch("cp.services.capacidade.agenda_service.AgendaPrevistaRepository"), \
             patch("cp.services.capacidade.agenda_service.AgendaLancamentoRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeDiaRepository"), \
             patch("cp.services.capacidade.agenda_service.FeriadoRepository"), \
             patch("cp.services.capacidade.agenda_service.IndisponibilidadeRepository"), \
             patch("cp.services.capacidade.agenda_service.TipoAtividadeRepository"), \
             patch("cp.services.capacidade.agenda_service.CapacidadeService"), \
             patch("cp.services.capacidade.agenda_service.AuditService"):
            
            from cp.services.capacidade.agenda_service import AgendaService
            return AgendaService(MagicMock())

    def test_obter_agenda_completa_com_capacidade(self, service):
        """Obtém agenda com capacidade materializada."""
        cap = mock_capacidade_dia(data=date(2026, 3, 10))
        service._capacidade_repo.listar_periodo.return_value = [cap]
        service._planejamento_repo.listar_por_usuario_periodo.return_value = []
        service._lancamento_repo.listar_por_usuario_periodo.return_value = []

        resultado = service.obter_agenda_completa(2, date(2026, 3, 10), date(2026, 3, 10))

        assert len(resultado) == 1
        assert resultado[0].teto_normal_min == 360
        assert resultado[0].eh_dia_util is True

    def test_obter_agenda_completa_sem_capacidade(self, service):
        """Obtém agenda sem capacidade materializada."""
        service._capacidade_repo.listar_periodo.return_value = []
        service._planejamento_repo.listar_por_usuario_periodo.return_value = []
        service._lancamento_repo.listar_por_usuario_periodo.return_value = []
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None

        resultado = service.obter_agenda_completa(2, date(2026, 3, 10), date(2026, 3, 10))

        assert len(resultado) == 1
        assert resultado[0].teto_normal_min == 360  # Dia útil sem feriado

    def test_obter_agenda_completa_feriado(self, service):
        """Obtém agenda de feriado."""
        service._capacidade_repo.listar_periodo.return_value = []
        service._planejamento_repo.listar_por_usuario_periodo.return_value = []
        service._lancamento_repo.listar_por_usuario_periodo.return_value = []
        service._feriado_repo.eh_feriado.return_value = True
        service._indisponibilidade_repo.buscar_para_data.return_value = None

        resultado = service.obter_agenda_completa(2, date(2026, 4, 21), date(2026, 4, 21))

        assert len(resultado) == 1
        assert resultado[0].teto_normal_min == 0  # Feriado

    def test_obter_agenda_completa_fim_de_semana(self, service):
        """Obtém agenda de fim de semana."""
        service._capacidade_repo.listar_periodo.return_value = []
        service._planejamento_repo.listar_por_usuario_periodo.return_value = []
        service._lancamento_repo.listar_por_usuario_periodo.return_value = []
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None

        # Sábado
        resultado = service.obter_agenda_completa(2, date(2026, 3, 14), date(2026, 3, 14))

        assert len(resultado) == 1
        assert resultado[0].teto_normal_min == 0  # Fim de semana

    def test_obter_agenda_completa_indisponibilidade(self, service):
        """Obtém agenda com indisponibilidade."""
        indisp = mock_indisponibilidade()
        tipo = mock_tipo_atividade(codigo=CodigoAtividade.FERIAS)
        
        service._capacidade_repo.listar_periodo.return_value = []
        service._planejamento_repo.listar_por_usuario_periodo.return_value = []
        service._lancamento_repo.listar_por_usuario_periodo.return_value = []
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = indisp
        service._tipo_atividade_repo.buscar_por_id.return_value = tipo

        resultado = service.obter_agenda_completa(2, date(2026, 7, 10), date(2026, 7, 10))

        assert len(resultado) == 1
        assert resultado[0].teto_normal_min == 0
        assert resultado[0].eh_indisponivel is True
        assert resultado[0].tipo_indisponibilidade == TipoIndisponibilidade.FERIAS

    def test_obter_agenda_completa_com_lancamentos(self, service):
        """Obtém agenda com lançamentos."""
        cap = mock_capacidade_dia(data=date(2026, 3, 10))
        lanc_normal = mock_lancamento(faixa=FaixaMinuto.NORMAL, minutos=120)
        lanc_extra = mock_lancamento(faixa=FaixaMinuto.EXTRA, minutos=60)
        tipo = mock_tipo_atividade()
        
        service._capacidade_repo.listar_periodo.return_value = [cap]
        service._planejamento_repo.listar_por_usuario_periodo.return_value = []
        service._lancamento_repo.listar_por_usuario_periodo.return_value = [lanc_normal, lanc_extra]
        service._tipo_atividade_repo.buscar_por_id.return_value = tipo

        resultado = service.obter_agenda_completa(2, date(2026, 3, 10), date(2026, 3, 10))

        assert resultado[0].apontado_normal_min == 120
        assert resultado[0].apontado_extra_min == 60
        assert resultado[0].minutos_ociosos == 240  # 360 - 120

    def test_obter_agenda_completa_periodo_multiplos_dias(self, service):
        """Obtém agenda de múltiplos dias."""
        service._capacidade_repo.listar_periodo.return_value = []
        service._planejamento_repo.listar_por_usuario_periodo.return_value = []
        service._lancamento_repo.listar_por_usuario_periodo.return_value = []
        service._feriado_repo.eh_feriado.return_value = False
        service._indisponibilidade_repo.buscar_para_data.return_value = None

        resultado = service.obter_agenda_completa(2, date(2026, 3, 9), date(2026, 3, 13))

        assert len(resultado) == 5  # Segunda a sexta
