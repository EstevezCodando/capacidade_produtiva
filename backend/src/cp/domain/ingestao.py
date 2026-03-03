from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class IngestaoExecucao:
    id: int
    iniciado_em: datetime
    status: str
    disparado_por: str
    finalizado_em: datetime | None = None
    counts: dict[str, int] = field(default_factory=dict)
    mensagem_erro: str | None = None


@dataclass(frozen=True)
class ResultadoIngestao:
    execucao_id: int
    status: str  # sucesso | falha
    counts: dict[str, int]
    mensagem_erro: str | None = None

    @property
    def sucesso(self) -> bool:
        return self.status == "sucesso"
