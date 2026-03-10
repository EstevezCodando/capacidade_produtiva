"""Verificação de qualidade de código.

Executa pytest, ruff (lint e format) e mypy em sequência.
Falha na primeira etapa que retornar erro.

Uso:
    uv run check
"""

from __future__ import annotations

import subprocess
import sys


def _run(cmd: list[str]) -> None:
    print(f"\n>> Executando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    _run(["uv", "run", "pytest"])
    _run(["uv", "run", "ruff", "check", "."])
    _run(["uv", "run", "ruff", "format", "."])
    _run(["uv", "run", "mypy", "src"])
