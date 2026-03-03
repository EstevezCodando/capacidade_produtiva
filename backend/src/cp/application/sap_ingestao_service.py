from __future__ import annotations

import logging

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from cp.domain.ingestao import ResultadoIngestao
from cp.infrastructure.ingestao_execucao_repository import IngestaoExecucaoRepository
from cp.infrastructure.sap_sync.sync import ResultadoTabela, sincronizar_sap_para_snapshot

logger = logging.getLogger(__name__)


class SapIngestaoService:
    """Governante da ingestão SAP.

    Responsabilidade: orquestrar execução, registrar logs e expor resultado.
    Motor único: sincronizar_sap_para_snapshot.
    """

    def __init__(
        self,
        engine_sap: Engine,
        engine_cp: Engine,
        repo_execucao: IngestaoExecucaoRepository,
    ) -> None:
        self._engine_sap = engine_sap
        self._engine_cp = engine_cp
        self._repo = repo_execucao

    def executar(self, disparado_por: str = "api") -> ResultadoIngestao:
        if self._repo.existe_em_andamento():
            ultima = self._repo.ultima_execucao()
            execucao_id = ultima.id if ultima else 0
            return ResultadoIngestao(
                execucao_id=execucao_id,
                status="falha",
                counts={},
                mensagem_erro="Já existe uma ingestão em andamento.",
            )

        try:
            execucao_id = self._repo.criar_execucao(disparado_por)
        except IntegrityError:
            ultima = self._repo.ultima_execucao()
            execucao_id = ultima.id if ultima else 0
            return ResultadoIngestao(
                execucao_id=execucao_id,
                status="falha",
                counts={},
                mensagem_erro="Já existe uma ingestão em andamento.",
            )

        try:
            resultados = sincronizar_sap_para_snapshot(self._engine_sap, self._engine_cp)
            counts = _consolidar_counts(resultados)
            self._repo.finalizar_execucao(execucao_id, "sucesso", counts)
            logger.info("Ingestão concluída com sucesso. execucao_id=%s", execucao_id)
            return ResultadoIngestao(execucao_id, "sucesso", counts)
        except Exception as exc:
            mensagem = str(exc)
            logger.exception("Falha na ingestão. execucao_id=%s erro=%s", execucao_id, mensagem)
            self._repo.finalizar_execucao(execucao_id, "falha", {}, mensagem)
            return ResultadoIngestao(execucao_id, "falha", {}, mensagem)


def _consolidar_counts(resultados: list[ResultadoTabela]) -> dict[str, int]:
    return {r.nome: int(r.lidas) for r in resultados}
