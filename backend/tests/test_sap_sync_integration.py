from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.infrastructure.sap_sync.sync import limpar_snapshot, sincronizar_sap_para_snapshot

_REGEX_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _sql_contar_snapshot(tabela: str) -> str:
    if not _REGEX_IDENT.fullmatch(tabela):
        raise ValueError(f"Nome de tabela inválido: {tabela!r}")
    return f'SELECT COUNT(*) FROM sap_snapshot."{tabela}"'


def _contar(engine_cp: Engine, tabela: str) -> int:
    with engine_cp.connect() as conn:
        return conn.execute(text(_sql_contar_snapshot(tabela))).scalar_one()


def test_sync_idempotente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    antes = _contar(engine_cp, "macrocontrole_atividade")

    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    depois = _contar(engine_cp, "macrocontrole_atividade")

    assert depois == antes


def test_limpeza_remove_finalizadas_antigas(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    with engine_cp.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO sap_snapshot.macrocontrole_atividade
                    (id, etapa_id, unidade_trabalho_id, usuario_id, tipo_situacao_id,
                     data_inicio, data_fim, observacao)
                VALUES
                    (9999, 4, 1, NULL, 4,
                     now() - interval '200 days',
                     now() - interval '181 days',
                     'teste: registro antigo para limpeza')
                ON CONFLICT (id) DO NOTHING
                """
            )
        )

    with engine_cp.connect() as conn:
        existe_antes = conn.execute(text("SELECT 1 FROM sap_snapshot.macrocontrole_atividade WHERE id = 9999")).scalar()
    assert existe_antes == 1

    apagadas = limpar_snapshot(engine_cp)

    with engine_cp.connect() as conn:
        existe_depois = conn.execute(text("SELECT 1 FROM sap_snapshot.macrocontrole_atividade WHERE id = 9999")).scalar()

    assert apagadas >= 1
    assert existe_depois is None
