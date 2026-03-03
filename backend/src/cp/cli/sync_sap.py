from __future__ import annotations

from cp.application.sap_sync_service import executar_sync_sap
from cp.config.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    resultados = executar_sync_sap(settings)
    for r in resultados:
        print(f"{r.nome}: lidas={r.lidas} gravadas={r.gravadas}")
