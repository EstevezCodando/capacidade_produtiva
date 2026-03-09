"""Pipeline de inicializacao completo do CapacidadeProdutiva.

Executa na ordem:
  1. check      — testes, lint, type-check
  2. alembic upgrade head — migracoes do banco CP
  3. sincronizar-sap      — ingestao do snapshot SAP -> CP
  4. uvicorn              — sobe a API na porta definida em CP_API_PORT (padrao 3050)

Uso:
    uv run inicializar

Em Docker o CMD chama este script diretamente.
O script usa subprocess para que cada etapa herde stdin/stdout/stderr
corretamente e o codigo de saida seja propagado.
"""

from __future__ import annotations

import subprocess
import sys


def _run(cmd: list[str], descricao: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {descricao}")
    print(f"  $ {' '.join(cmd)}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n[ERRO] Etapa falhou: {descricao} (codigo {result.returncode})")
        sys.exit(result.returncode)


def main() -> None:
    # 1. Qualidade: testes + lint + type-check
    _run(["uv", "run", "check"], "Verificacao de qualidade (testes, lint, mypy)")

    # 2. Migracoes
    _run(["uv", "run", "alembic", "upgrade", "head"], "Migracoes Alembic (upgrade head)")

    # 3. Sincronizacao SAP
    _run(["uv", "run", "sincronizar-sap"], "Sincronizacao SAP -> sap_snapshot")

    # 4. API — porta lida do ambiente, padrao 3050
    import os

    porta = os.environ.get("CP_API_PORT", "3050")
    _run(
        [
            "uv",
            "run",
            "uvicorn",
            "cp.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            porta,
        ],
        f"API CapacidadeProdutiva em 0.0.0.0:{porta}",
    )
