"""Mapeamento centralizado de exceções de domínio para HTTPException.

Elimina a duplicação de _handle_exception() nos routers de agenda e capacidade.
"""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException, status

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
    PermissaoError,
    RegistroNaoEncontradoError,
    ValidacaoError,
    VigenciaConflitanteError,
)

# Mapeamento estático: tipo de exceção → código HTTP
_EXCECAO_PARA_STATUS: list[tuple[type[Exception], int]] = [
    (DataFuturaError, status.HTTP_403_FORBIDDEN),
    (DiaConsolidadoError, status.HTTP_403_FORBIDDEN),
    (AcessoNegadoError, status.HTTP_403_FORBIDDEN),
    (PermissaoError, status.HTTP_403_FORBIDDEN),
    (RegistroNaoEncontradoError, status.HTTP_404_NOT_FOUND),
    (LimiteCapacidadeExcedidoError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (DiaIndisponivelError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (IntervaloInvalidoError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (FeriadoDuplicadoError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (IndisponibilidadeSobrepostaError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (VigenciaConflitanteError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (ValidacaoError, status.HTTP_422_UNPROCESSABLE_ENTITY),
    (CapacidadeError, status.HTTP_400_BAD_REQUEST),
]


def handle_domain_exception(exc: Exception) -> NoReturn:
    """Converte exceções de domínio em HTTPException.

    Percorre o mapeamento estático em ordem de prioridade.
    Exceções não mapeadas são relançadas para o handler global do FastAPI.

    Raises:
        HTTPException: para exceções de domínio conhecidas.
        Exception: relança exceções desconhecidas.
    """
    for exc_type, http_status in _EXCECAO_PARA_STATUS:
        if isinstance(exc, exc_type):
            raise HTTPException(status_code=http_status, detail=str(exc))
    raise exc
