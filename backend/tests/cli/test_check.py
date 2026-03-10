# caminho: backend/tests/cli/test_check.py
"""Testes do módulo de verificação de qualidade."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cp.cli import check


class TestRun:
    """Testes da função _run."""

    def test_executa_comando_com_sucesso(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            # Não deve levantar exceção
            check._run(["echo", "hello"])
            mock_run.assert_called_once_with(["echo", "hello"])

    def test_falha_com_exit_code_nao_zero(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with pytest.raises(SystemExit) as exc_info:
                check._run(["false"])
            assert exc_info.value.code == 1


class TestMain:
    """Testes do fluxo principal."""

    def test_executa_todas_as_etapas(self) -> None:
        comandos_executados: list[list[str]] = []

        def mock_run(cmd: list[str]) -> MagicMock:
            comandos_executados.append(cmd)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=mock_run):
            check.main()

        # Verifica que os 4 comandos foram executados
        assert len(comandos_executados) == 4
        assert comandos_executados[0] == ["uv", "run", "pytest"]
        assert comandos_executados[1] == ["uv", "run", "ruff", "check", "."]
        assert comandos_executados[2] == ["uv", "run", "ruff", "format", "."]
        assert comandos_executados[3] == ["uv", "run", "mypy", "src"]

    def test_para_na_primeira_falha(self) -> None:
        comandos_executados: list[list[str]] = []

        def mock_run(cmd: list[str]) -> MagicMock:
            comandos_executados.append(cmd)
            # Falha no segundo comando (ruff check)
            if "ruff" in cmd and "check" in cmd:
                return MagicMock(returncode=1)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=mock_run):
            with pytest.raises(SystemExit) as exc_info:
                check.main()

        assert exc_info.value.code == 1
        # Parou após pytest e ruff check (2 comandos)
        assert len(comandos_executados) == 2
