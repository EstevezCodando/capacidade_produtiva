"""
Testes unitários para create_config.py.

Todos os testes usam mocks/monkeypatching — nenhuma conexão real é feita.
Garante que a lógica de validação, leitura e gravação funciona corretamente
e que erros são propagados de forma legível.
"""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import create_config as cc
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_sap_config_env(tmp_path: Path) -> Path:
    """Cria um config.env falso do SAP com JWT_SECRET válido."""
    config_file = tmp_path / "config.env"
    config_file.write_text(
        "NODE_TLS_REJECT_UNAUTHORIZED=0\n"
        "PORT=3013\n"
        "DB_SERVER=localhost\n"
        "JWT_SECRET=abc123secret_reaproveitado\n"
        "AUTH_SERVER=http://localhost:3010\n",
        encoding="utf-8",
    )
    return config_file


@pytest.fixture()
def fake_sap_config_env_no_secret(tmp_path: Path) -> Path:
    """Config.env do SAP sem JWT_SECRET."""
    config_file = tmp_path / "config.env"
    config_file.write_text("PORT=3013\n", encoding="utf-8")
    return config_file


@pytest.fixture()
def fake_sap_config_env_empty_secret(tmp_path: Path) -> Path:
    """Config.env do SAP com JWT_SECRET vazio."""
    config_file = tmp_path / "config.env"
    config_file.write_text("JWT_SECRET=\n", encoding="utf-8")
    return config_file


# ---------------------------------------------------------------------------
# read_jwt_secret_from_sap_config
# ---------------------------------------------------------------------------


class TestReadJwtSecret:
    def test_lê_secret_com_sucesso(self, fake_sap_config_env: Path) -> None:
        secret = cc.read_jwt_secret_from_sap_config(fake_sap_config_env)
        assert secret == "abc123secret_reaproveitado"

    def test_arquivo_inexistente_levanta_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="não encontrado"):
            cc.read_jwt_secret_from_sap_config(tmp_path / "nao_existe.env")

    def test_arquivo_sem_jwt_secret_levanta_key_error(
        self, fake_sap_config_env_no_secret: Path
    ) -> None:
        with pytest.raises(KeyError, match="JWT_SECRET não encontrado"):
            cc.read_jwt_secret_from_sap_config(fake_sap_config_env_no_secret)

    def test_jwt_secret_vazio_levanta_value_error(
        self, fake_sap_config_env_empty_secret: Path
    ) -> None:
        with pytest.raises(ValueError, match="JWT_SECRET está vazio"):
            cc.read_jwt_secret_from_sap_config(fake_sap_config_env_empty_secret)


# ---------------------------------------------------------------------------
# verify_auth_server
# ---------------------------------------------------------------------------


class TestVerifyAuthServer:
    def test_url_sem_schema_levanta_value_error(self) -> None:
        with pytest.raises(ValueError, match="http:// ou https://"):
            cc.verify_auth_server("meu-servidor:3010")

    def test_servidor_operacional_não_levanta(self) -> None:
        """Simula resposta correta do Serviço de Autenticação."""
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = (
            b'{"message": "Servi\xc3\xa7o de autentica\xc3\xa7\xc3\xa3o operacional"}'
        )
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            cc.verify_auth_server("http://localhost:3010")  # não deve levantar

    def test_servidor_retorna_http_500_levanta_runtime_error(self) -> None:
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.read.return_value = b"{}"
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            with pytest.raises(RuntimeError, match="HTTP 500"):
                cc.verify_auth_server("http://localhost:3010")

    def test_servidor_com_mensagem_errada_levanta_runtime_error(self) -> None:
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"message": "outro servico"}'
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            with pytest.raises(RuntimeError, match="Resposta inesperada"):
                cc.verify_auth_server("http://localhost:3010")

    def test_falha_de_rede_levanta_runtime_error(self) -> None:
        with patch("http.client.HTTPConnection", side_effect=OSError("conexão recusada")):
            with pytest.raises(RuntimeError, match="Erro ao se comunicar"):
                cc.verify_auth_server("http://localhost:9999")

    def test_resposta_nao_json_levanta_runtime_error(self) -> None:
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"not json at all"
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            with pytest.raises(RuntimeError, match="não-JSON"):
                cc.verify_auth_server("http://localhost:3010")


# ---------------------------------------------------------------------------
# verify_sap_connection
# ---------------------------------------------------------------------------


class TestVerifySapConnection:
    def test_conexão_bem_sucedida_não_levanta(self) -> None:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with patch("psycopg2.connect", return_value=mock_conn):
            cc.verify_sap_connection("localhost", 5432, "sap", "user", "pass")

        mock_cur.execute.assert_called_once_with("SELECT 1")
        mock_cur.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_falha_de_conexão_levanta_runtime_error(self) -> None:
        import psycopg2  # type: ignore[import-untyped]

        with patch(
            "psycopg2.connect",
            side_effect=psycopg2.OperationalError("connection refused"),
        ):
            with pytest.raises(RuntimeError, match="Falha ao conectar no banco SAP"):
                cc.verify_sap_connection("localhost", 5432, "sap", "user", "senha_errada")

    def test_psycopg2_nao_instalado_levanta_runtime_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simula ambiente sem psycopg2 instalado."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "psycopg2":
                raise ImportError("No module named 'psycopg2'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(RuntimeError, match="psycopg2-binary não está instalado"):
            cc.verify_sap_connection("localhost", 5432, "sap", "user", "pass")


# ---------------------------------------------------------------------------
# write_config_env
# ---------------------------------------------------------------------------


class TestWriteConfigEnv:
    def test_cria_arquivo_com_todas_as_variáveis(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Redireciona _SERVER_DIR e _CONFIG_ENV para tmp_path
        monkeypatch.setattr(cc, "_SERVER_DIR", tmp_path / "server")
        monkeypatch.setattr(cc, "_CONFIG_ENV", tmp_path / "server" / "config.env")

        cc.write_config_env(
            cp_db_host="cp-host",
            cp_db_port=5432,
            cp_db_name="capacidade_produtiva",
            cp_db_user="cp_user",
            cp_db_password="cp_pass",
            sap_db_host="sap-host",
            sap_db_port=5433,
            sap_db_name="sap",
            sap_db_user="sap_user",
            sap_db_password="sap_pass",
            auth_server_url="http://auth:3010",
            jwt_secret="super_secret_token",
            app_port=8000,
            log_level="INFO",
        )

        config_path = tmp_path / "server" / "config.env"
        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")

        # Variáveis obrigatórias presentes
        assert "CP_DB_HOST=cp-host" in content
        assert "CP_DB_PORT=5432" in content
        assert "CP_DB_NAME=capacidade_produtiva" in content
        assert "CP_DB_USER=cp_user" in content
        assert "CP_DB_PASSWORD=cp_pass" in content
        assert "SAP_DB_HOST=sap-host" in content
        assert "SAP_DB_PORT=5433" in content
        assert "SAP_DB_NAME=sap" in content
        assert "SAP_DB_USER=sap_user" in content
        assert "SAP_DB_PASSWORD=sap_pass" in content
        assert "AUTH_SERVER=http://auth:3010" in content
        assert "JWT_SECRET=super_secret_token" in content
        assert "APP_PORT=8000" in content
        assert "LOG_LEVEL=INFO" in content

    def test_cria_diretório_server_se_não_existir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        server_dir = tmp_path / "server"
        assert not server_dir.exists()

        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        cc.write_config_env(
            cp_db_host="h",
            cp_db_port=5432,
            cp_db_name="d",
            cp_db_user="u",
            cp_db_password="p",
            sap_db_host="h2",
            sap_db_port=5432,
            sap_db_name="sap",
            sap_db_user="u2",
            sap_db_password="p2",
            auth_server_url="http://auth:3010",
            jwt_secret="s",
            app_port=8000,
            log_level="INFO",
        )

        assert server_dir.exists()
        assert (server_dir / "config.env").exists()


# ---------------------------------------------------------------------------
# Argparse / CLI
# ---------------------------------------------------------------------------


class TestArgumentParser:
    def test_parser_aceita_todas_as_flags_longas(self) -> None:
        parser = cc._build_parser()
        args = parser.parse_args(
            [
                "--cp-db-host",
                "cp-host",
                "--cp-db-port",
                "5432",
                "--cp-db-name",
                "capacidade_produtiva",
                "--cp-db-user",
                "cp_user",
                "--cp-db-password",
                "cp_pass",
                "--sap-db-host",
                "sap-host",
                "--sap-db-port",
                "5433",
                "--sap-db-name",
                "sap",
                "--sap-db-user",
                "sap_user",
                "--sap-db-password",
                "sap_pass",
                "--auth-server-url",
                "http://auth:3010",
                "--sap-config-env",
                "/opt/sap/server/config.env",
                "--app-port",
                "8000",
                "--log-level",
                "INFO",
                "--overwrite",
            ]
        )
        assert args.cp_db_host == "cp-host"
        assert args.sap_db_host == "sap-host"
        assert args.auth_server_url == "http://auth:3010"
        assert args.overwrite is True

    def test_parser_log_level_invalido_falha(self) -> None:
        parser = cc._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--log-level", "VERBOSE"])

    def test_overwrite_default_é_false(self) -> None:
        parser = cc._build_parser()
        args = parser.parse_args([])
        assert args.overwrite is False


# ---------------------------------------------------------------------------
# create_config — fluxo completo (integração com mocks)
# ---------------------------------------------------------------------------


class TestCreateConfigFlow:
    def _make_args(self, overwrite: bool = False, **kwargs: str) -> argparse.Namespace:
        """Cria um namespace de args com todos os campos preenchidos."""
        defaults = {
            "cp_db_host": "cp-host",
            "cp_db_port": "5432",
            "cp_db_name": "capacidade_produtiva",
            "cp_db_user": "cp_user",
            "cp_db_password": "cp_pass",
            "sap_db_host": "sap-host",
            "sap_db_port": "5432",
            "sap_db_name": "sap",
            "sap_db_user": "sap_user",
            "sap_db_password": "sap_pass",
            "auth_server_url": "http://auth:3010",
            "sap_config_env": None,  # será preenchido em cada teste
            "app_port": "8000",
            "log_level": "INFO",
            "overwrite": overwrite,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_fluxo_completo_grava_config_env(
        self,
        tmp_path: Path,
        fake_sap_config_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        args = self._make_args(sap_config_env=str(fake_sap_config_env))

        with (
            patch.object(cc, "verify_sap_connection"),
            patch.object(cc, "verify_auth_server"),
        ):
            cc.create_config(args)

        assert (server_dir / "config.env").exists()
        content = (server_dir / "config.env").read_text()
        assert "JWT_SECRET=abc123secret_reaproveitado" in content
        assert "AUTH_SERVER=http://auth:3010" in content

    def test_config_env_existente_sem_overwrite_termina_com_exit(
        self,
        tmp_path: Path,
        fake_sap_config_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        existing = server_dir / "config.env"
        existing.write_text("existente", encoding="utf-8")

        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", existing)

        args = self._make_args(sap_config_env=str(fake_sap_config_env))

        with pytest.raises(SystemExit) as exc_info:
            cc.create_config(args)
        assert exc_info.value.code == 1

    def test_config_env_existente_com_overwrite_sobrescreve(
        self,
        tmp_path: Path,
        fake_sap_config_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        existing = server_dir / "config.env"
        existing.write_text("conteudo_antigo", encoding="utf-8")

        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", existing)

        args = self._make_args(overwrite=True, sap_config_env=str(fake_sap_config_env))

        with (
            patch.object(cc, "verify_sap_connection"),
            patch.object(cc, "verify_auth_server"),
        ):
            cc.create_config(args)

        content = existing.read_text()
        assert "conteudo_antigo" not in content
        assert "JWT_SECRET=" in content

    def test_falha_na_conexao_sap_termina_com_exit(
        self,
        tmp_path: Path,
        fake_sap_config_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        args = self._make_args(sap_config_env=str(fake_sap_config_env))

        with patch.object(
            cc, "verify_sap_connection", side_effect=RuntimeError("conexão recusada")
        ):
            with pytest.raises(SystemExit) as exc_info:
                cc.create_config(args)
        assert exc_info.value.code == 1

    def test_falha_no_auth_server_termina_com_exit(
        self,
        tmp_path: Path,
        fake_sap_config_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        args = self._make_args(sap_config_env=str(fake_sap_config_env))

        with (
            patch.object(cc, "verify_sap_connection"),
            patch.object(cc, "verify_auth_server", side_effect=RuntimeError("auth offline")),
        ):
            with pytest.raises(SystemExit) as exc_info:
                cc.create_config(args)
        assert exc_info.value.code == 1

    def test_auth_url_tem_barra_final_removida(
        self,
        tmp_path: Path,
        fake_sap_config_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """URL com barra final deve ser normalizada antes de gravar."""
        server_dir = tmp_path / "server"
        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        args = self._make_args(
            auth_server_url="http://auth:3010/",
            sap_config_env=str(fake_sap_config_env),
        )

        with (
            patch.object(cc, "verify_sap_connection"),
            patch.object(cc, "verify_auth_server"),
        ):
            cc.create_config(args)

        content = (server_dir / "config.env").read_text()
        assert "AUTH_SERVER=http://auth:3010\n" in content
        assert "AUTH_SERVER=http://auth:3010/" not in content
