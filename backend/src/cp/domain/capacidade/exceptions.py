"""Exceções do domínio de Capacidade.

Define exceções específicas para validação e regras de negócio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


class CapacidadeError(Exception):
    """Exceção base do módulo de capacidade."""

    pass


class ValidacaoError(CapacidadeError):
    """Erro de validação de dados de entrada."""

    pass


class PermissaoError(CapacidadeError):
    """Erro de permissão de acesso."""

    pass


class LimiteCapacidadeExcedidoError(ValidacaoError):
    """Minutos normais excedem a capacidade do dia.

    Attributes:
        capacidade_disponivel: minutos normais ainda disponíveis
        minutos_solicitados: minutos que se tentou alocar
        minutos_ja_alocados: minutos normais já alocados no dia
    """

    def __init__(
        self,
        capacidade_disponivel: int,
        minutos_solicitados: int,
        minutos_ja_alocados: int,
    ) -> None:
        self.capacidade_disponivel = capacidade_disponivel
        self.minutos_solicitados = minutos_solicitados
        self.minutos_ja_alocados = minutos_ja_alocados
        super().__init__(
            f"Minutos normais excedem a capacidade do dia. "
            f"Disponível: {capacidade_disponivel}, Solicitado: {minutos_solicitados}, "
            f"Já alocado: {minutos_ja_alocados}"
        )


class DataFuturaError(PermissaoError):
    """Operador não pode lançar em data futura."""

    def __init__(self, data_lancamento: date, data_atual: date) -> None:
        self.data_lancamento = data_lancamento
        self.data_atual = data_atual
        super().__init__(
            f"Operador não pode lançar em data futura. "
            f"Data do lançamento: {data_lancamento}, Data atual: {data_atual}"
        )


class DiaConsolidadoError(PermissaoError):
    """Dia já consolidado não permite alterações normais."""

    def __init__(self, data: date, permite_extra: bool = True) -> None:
        self.data = data
        self.permite_extra = permite_extra
        msg = f"Dia {data} está consolidado."
        if permite_extra:
            msg += " Apenas lançamentos extras são permitidos."
        else:
            msg += " Nenhuma alteração permitida."
        super().__init__(msg)


class DiaIndisponivelError(ValidacaoError):
    """Dia indisponível não permite alocação normal."""

    def __init__(self, data: date, tipo: str) -> None:
        self.data = data
        self.tipo = tipo
        super().__init__(
            f"Dia {data} está marcado como indisponível ({tipo}). "
            f"Alocação normal não permitida."
        )


class IntervaloInvalidoError(ValidacaoError):
    """Intervalo de datas inválido."""

    def __init__(self, data_inicio: date, data_fim: date) -> None:
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        super().__init__(f"Intervalo inválido: data_fim ({data_fim}) < data_inicio ({data_inicio})")


class RegistroNaoEncontradoError(CapacidadeError):
    """Registro não encontrado no banco de dados."""

    def __init__(self, entidade: str, identificador: Any) -> None:
        self.entidade = entidade
        self.identificador = identificador
        super().__init__(f"{entidade} não encontrado(a): {identificador}")


class AcessoNegadoError(PermissaoError):
    """Usuário não tem permissão para acessar este recurso."""

    def __init__(self, usuario_id: int, recurso: str) -> None:
        self.usuario_id = usuario_id
        self.recurso = recurso
        super().__init__(f"Usuário {usuario_id} não tem permissão para acessar {recurso}")


class VigenciaConflitanteError(ValidacaoError):
    """Conflito de vigência entre parâmetros."""

    def __init__(self, data_inicio: date, data_fim: date | None) -> None:
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        super().__init__(
            f"Já existe parâmetro vigente no período {data_inicio} - {data_fim or 'indefinido'}"
        )


class FeriadoDuplicadoError(ValidacaoError):
    """Feriado já cadastrado para esta data."""

    def __init__(self, data: date) -> None:
        self.data = data
        super().__init__(f"Já existe feriado cadastrado para {data}")


class IndisponibilidadeSobrepostaError(ValidacaoError):
    """Indisponibilidade sobreposta a outra existente."""

    def __init__(self, usuario_id: int, data_inicio: date, data_fim: date) -> None:
        self.usuario_id = usuario_id
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        super().__init__(
            f"Indisponibilidade sobreposta para usuário {usuario_id} "
            f"no período {data_inicio} - {data_fim}"
        )


@dataclass
class PendenciaConsolidacao:
    """Representa uma pendência impeditiva de consolidação."""

    usuario_id: int
    data: date
    tipo: str
    motivo: str


@dataclass
class ResultadoConsolidacao:
    """Resultado de tentativa de consolidação."""

    consolidado: bool
    pendencias: list[PendenciaConsolidacao] = field(default_factory=list)
    mensagem: str = ""
