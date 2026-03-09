"""Rotas de saude e diagnostico do servico.

Publicas — sem autenticacao.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["infra"])


class HealthResponse(BaseModel):
    status: str


@router.get("/health", summary="Health check")
def health() -> HealthResponse:
    """Confirma que o servico esta no ar."""
    return HealthResponse(status="ok")
