"""Domínio de Capacidade.

Exporta enums, modelos, schemas e exceções do módulo.
"""

from cp.domain.capacidade.enums import (
    AcaoAuditoria,
    CodigoAtividade,
    FaixaMinuto,
    GrupoAtividade,
    StatusDia,
    TipoIndisponibilidade,
    TipoPendencia,
)
from cp.domain.capacidade.exceptions import (
    AcessoNegadoError,
    CapacidadeError,
    DataFuturaError,
    DiaConsolidadoError,
    DiaIndisponivelError,
    FeriadoDuplicadoError,
    IndisponibilidadeSobrepostaError,
    IntervaloInvalidoError,
    LimiteCapacidadeExcedidoError,
    PendenciaConsolidacao,
    PermissaoError,
    RegistroNaoEncontradoError,
    ResultadoConsolidacao,
    ValidacaoError,
    VigenciaConflitanteError,
)
from cp.domain.capacidade.models import (
    AgendaLancamento,
    AgendaPrevistaAdmin,
    AuditLog,
    Base,
    CapacidadeDia,
    Feriado,
    IndisponibilidadeUsuario,
    ParametroCapacidade,
    TipoAtividade,
)

__all__ = [
    # Enums
    "AcaoAuditoria",
    "CodigoAtividade",
    "FaixaMinuto",
    "GrupoAtividade",
    "StatusDia",
    "TipoIndisponibilidade",
    "TipoPendencia",
    # Exceções
    "AcessoNegadoError",
    "CapacidadeError",
    "DataFuturaError",
    "DiaConsolidadoError",
    "DiaIndisponivelError",
    "FeriadoDuplicadoError",
    "IndisponibilidadeSobrepostaError",
    "IntervaloInvalidoError",
    "LimiteCapacidadeExcedidoError",
    "PendenciaConsolidacao",
    "PermissaoError",
    "RegistroNaoEncontradoError",
    "ResultadoConsolidacao",
    "ValidacaoError",
    "VigenciaConflitanteError",
    # Modelos
    "AgendaLancamento",
    "AgendaPrevistaAdmin",
    "AuditLog",
    "Base",
    "CapacidadeDia",
    "Feriado",
    "IndisponibilidadeUsuario",
    "ParametroCapacidade",
    "TipoAtividade",
]
