from __future__ import annotations

from sqlalchemy.engine import Engine

from cp.application.sync_history_service import finalizar_sync, registrar_inicio_sync
from cp.config.settings import Settings
from cp.infrastructure.db import criar_engine_cp, criar_engine_sap
from cp.infrastructure.sap_sync.sync import ResultadoTabela, sincronizar_sap_para_snapshot


def executar_sync_sap(settings: Settings) -> list[ResultadoTabela]:
    engine_cp = criar_engine_cp(settings)
    engine_sap = criar_engine_sap(settings)
    return executar_sync_sap_com_engines(engine_sap, engine_cp, origem="cli")


def executar_sync_sap_com_engines(
    engine_sap: Engine,
    engine_cp: Engine,
    *,
    origem: str,
) -> list[ResultadoTabela]:
    execucao_id = registrar_inicio_sync(engine_cp, origem)
    try:
        resultados = sincronizar_sap_para_snapshot(engine_sap, engine_cp)
        total_lidas = sum(resultado.lidas for resultado in resultados)
        total_gravadas = sum(resultado.gravadas for resultado in resultados)
        finalizar_sync(
            engine_cp,
            execucao_id,
            status="sucesso",
            mensagem=f"Sincronização concluída com sucesso. lidas={total_lidas} gravadas={total_gravadas}",
        )
        return resultados
    except Exception as exc:
        finalizar_sync(
            engine_cp,
            execucao_id,
            status="falha",
            mensagem=str(exc),
        )
        raise
