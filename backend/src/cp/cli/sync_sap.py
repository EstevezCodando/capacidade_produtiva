from __future__ import annotations

from cp.application.sap_sync_service import executar_sync_sap
from cp.config.logging_config import configurar_logging
from cp.config.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    configurar_logging(settings.cp_log_level, settings.cp_sql_log_level)

    resultado = executar_sync_sap(settings, disparado_por="cli")
    print(f"execucao_id={resultado.execucao_id} status={resultado.status}")
    if resultado.mensagem_erro:
        print(f"erro={resultado.mensagem_erro}")
    for nome, lidas in resultado.counts.items():
        print(f"{nome}: lidas={lidas}")
