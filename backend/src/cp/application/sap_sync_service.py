from __future__ import annotations

from cp.config.settings import Settings
from cp.infrastructure.db import criar_engine_cp, criar_engine_sap
from cp.infrastructure.sap_sync.sync import ResultadoTabela, sincronizar_sap_para_snapshot


def executar_sync_sap(settings: Settings) -> list[ResultadoTabela]:
    engine_cp = criar_engine_cp(settings)
    engine_sap = criar_engine_sap(settings)
    return sincronizar_sap_para_snapshot(engine_sap, engine_cp)
