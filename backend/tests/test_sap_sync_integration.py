from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from cp.infrastructure.sap_sync.sync import limpar_snapshot, sincronizar_sap_para_snapshot


def _contar(engine_cp: Engine, tabela: str) -> int:
    with engine_cp.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM sap_snapshot.{tabela}")).scalar_one()


def test_sync_idempotente(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Rodar sync duas vezes seguidas não altera a contagem de registros."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)
    resultados_segunda = sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    gravadas_por_tabela = {r.nome: r.gravadas for r in resultados_segunda}
    assert gravadas_por_tabela["macrocontrole_atividade"] == 0


def test_limpeza_remove_finalizadas_antigas(engine_sap: Engine, engine_cp: Engine, sap_seed: None) -> None:
    """Limpeza deve remover atividades finalizadas há mais de 180 dias."""
    sincronizar_sap_para_snapshot(engine_sap, engine_cp)

    # Insere diretamente no snapshot um registro antigo (fora da janela do sync)
    with engine_cp.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO sap_snapshot.macrocontrole_atividade
                (id, etapa_id, unidade_trabalho_id, usuario_id, tipo_situacao_id,
                 data_inicio, data_fim, observacao)
            VALUES
                (9999, 4, 1, NULL, 4,
                 now() - interval '200 days',
                 now() - interval '181 days',
                 'teste: registro antigo para limpeza')
            ON CONFLICT (id) DO NOTHING
        """)
        )

    apagadas = limpar_snapshot(engine_cp)
    assert apagadas >= 1
