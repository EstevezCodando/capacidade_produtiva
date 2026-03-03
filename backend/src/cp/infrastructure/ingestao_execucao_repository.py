from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.domain.ingestao import IngestaoExecucao


class IngestaoExecucaoRepository:
    def __init__(self, engine_cp: Engine) -> None:
        self._engine_cp = engine_cp

    def criar_execucao(self, disparado_por: str) -> int:
        with self._engine_cp.begin() as conn:
            row = conn.execute(
                text(
                    """
                    INSERT INTO log.ingestao_execucao (disparado_por)
                    VALUES (:disparado_por)
                    RETURNING id
                    """
                ),
                {"disparado_por": disparado_por},
            ).fetchone()
            if not row:
                raise RuntimeError("Falha ao criar execução de ingestão.")
            return int(row.id)

    def finalizar_execucao(
        self,
        execucao_id: int,
        status: str,
        counts: dict[str, int],
        mensagem_erro: str | None = None,
    ) -> None:
        with self._engine_cp.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE log.ingestao_execucao
                    SET
                        finalizado_em = now(),
                        status        = :status,
                        counts        = :counts::jsonb,
                        mensagem_erro = :mensagem_erro
                    WHERE id = :id
                    """
                ),
                {
                    "id": execucao_id,
                    "status": status,
                    "counts": json.dumps(counts, ensure_ascii=False),
                    "mensagem_erro": mensagem_erro,
                },
            )

    def ultima_execucao(self) -> IngestaoExecucao | None:
        with self._engine_cp.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, iniciado_em, finalizado_em, status,
                           disparado_por, counts, mensagem_erro
                    FROM log.ingestao_execucao
                    ORDER BY iniciado_em DESC
                    LIMIT 1
                    """
                )
            ).fetchone()
        return self._mapear(row)

    def ultima_bem_sucedida(self) -> IngestaoExecucao | None:
        with self._engine_cp.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, iniciado_em, finalizado_em, status,
                           disparado_por, counts, mensagem_erro
                    FROM log.ingestao_execucao
                    WHERE status = 'sucesso'
                    ORDER BY finalizado_em DESC
                    LIMIT 1
                    """
                )
            ).fetchone()
        return self._mapear(row)

    def existe_em_andamento(self) -> bool:
        with self._engine_cp.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM log.ingestao_execucao
                    WHERE status = 'em_andamento'
                    LIMIT 1
                    """
                )
            ).fetchone()
        return row is not None

    def _mapear(self, row) -> IngestaoExecucao | None:
        if not row:
            return None
        return IngestaoExecucao(
            id=int(row.id),
            iniciado_em=row.iniciado_em,
            finalizado_em=row.finalizado_em,
            status=row.status,
            disparado_por=row.disparado_por,
            counts=row.counts or {},
            mensagem_erro=row.mensagem_erro,
        )
