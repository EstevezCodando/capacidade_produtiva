from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from cp.application.sap_ingestao_service import SapIngestaoService
from cp.domain.ingestao import ResultadoIngestao

router = APIRouter(prefix="/api/admin/sap", tags=["admin", "sap"])


def _get_ingestao_service(request: Request) -> SapIngestaoService:
    return request.app.state.sap_ingestao_service


@router.post("/sincronizar", response_model=None)
def sincronizar_sap(service: SapIngestaoService = Depends(_get_ingestao_service)) -> dict[str, object]:
    resultado: ResultadoIngestao = service.executar(disparado_por="api")
    return {
        "execucao_id": resultado.execucao_id,
        "status": resultado.status,
        "counts": resultado.counts,
        "mensagem_erro": resultado.mensagem_erro,
    }
