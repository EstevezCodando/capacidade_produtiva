from __future__ import annotations

from unittest.mock import Mock

from cp.application.sap_sync_service import executar_sync_sap
from cp.infrastructure.sap_sync.sync import ResultadoTabela


def test_executar_sync_sap_chama_pipeline(monkeypatch: object) -> None:
    settings_fake = Mock()

    engine_cp = Mock()
    engine_sap = Mock()

    monkeypatch.setattr("cp.application.sap_sync_service.criar_engine_cp", lambda _: engine_cp)
    monkeypatch.setattr("cp.application.sap_sync_service.criar_engine_sap", lambda _: engine_sap)

    esperado = [ResultadoTabela(nome="x", lidas=1, gravadas=1)]
    monkeypatch.setattr(
        "cp.application.sap_sync_service.sincronizar_sap_para_snapshot",
        lambda _sap, _cp: esperado,
    )

    res = executar_sync_sap(settings_fake)
    assert res == esperado
