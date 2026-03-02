"""
Testes unitários para create_config.py.

Todos os testes usam mocks/monkeypatching — nenhuma conexão real é feita.
Garante que a lógica de validação, leitura e gravação funciona corretamente
e que erros são propagados de forma legível.
"""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import cp.cli.create_config as cc

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# generate_jwt_secret
# ---------------------------------------------------------------------------


class TestGenerateJwtSecret:
    def test_retorna_string_de_128_chars(self) -> None:
        secret = cc.generate_jwt_secret()
        assert isinstance(secret, str)
        assert len(secret) == 128  # 64 bytes = 128 hex chars

    def test_apenas_caracteres_hex(self) -> None:
        secret = cc.generate_jwt_secret()
        assert all(c in "0123456789abcdef" for c in secret)

    def test_secrets_diferentes_a_cada_chamada(self) -> None:
        assert cc.generate_jwt_secret() != cc.generate_jwt_secret()


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
        mock_response.read.return_value = b'{"message": "Servi\xc3\xa7o de autentica\xc3\xa7\xc3\xa3o operacional"}'
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

        with patch("cp.cli.create_config.psycopg2") as mock_pg:
            mock_pg.connect.return_value = mock_conn
            cc.verify_sap_connection("localhost", 5432, "sap", "user", "pass")

        mock_cur.execute.assert_called_once_with("SELECT 1")
        mock_cur.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_falha_de_conexão_levanta_runtime_error(self) -> None:
        with patch("cp.cli.create_config.psycopg2") as mock_pg:
            mock_pg.OperationalError = Exception
            mock_pg.connect.side_effect = Exception("connection refused")

            with pytest.raises(RuntimeError, match="Falha ao conectar no banco SAP"):
                cc.verify_sap_connection("localhost", 5432, "sap", "user", "senha_errada")


# ---------------------------------------------------------------------------
# _ask
# ---------------------------------------------------------------------------


class TestAsk:
    def test_retorna_default_quando_entrada_vazia(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert cc._ask("Campo", default="valor") == "valor"

    def test_campo_obrigatorio_vazio_levanta_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "")
        with pytest.raises(ValueError, match="Campo obrigatório não informado"):
            cc._ask("Campo sem default")

    def test_secret_usa_getpass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cp.cli.create_config.getpass.getpass", lambda _: "senha")
        assert cc._ask("Senha", secret=True) == "senha"


# ---------------------------------------------------------------------------
# verify_auth_server — branch HTTPS
# ---------------------------------------------------------------------------


class TestVerifyAuthServerHttps:
    def test_url_https_conecta_via_ssl(self) -> None:
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"message": "Servi\xc3\xa7o de autentica\xc3\xa7\xc3\xa3o operacional"}'
        mock_conn.getresponse.return_value = mock_response

        with patch("cp.cli.create_config.http.client.HTTPSConnection", return_value=mock_conn):
            cc.verify_auth_server("https://auth:3010")

        mock_conn.request.assert_called_once_with("GET", "/api")


# ---------------------------------------------------------------------------
# _http_request — branches HTTPS e erros
# ---------------------------------------------------------------------------


class TestHttpRequest:
    def test_erro_de_rede_levanta_runtime_error(self) -> None:
        with patch("cp.cli.create_config.http.client.HTTPConnection") as mock_cls:
            mock_cls.return_value.request.side_effect = OSError("timeout")
            with pytest.raises(RuntimeError, match="Erro de rede"):
                cc._http_request("GET", "http://host:80/api")

    def test_resposta_nao_json_levanta_runtime_error(self) -> None:
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"not json"
        mock_conn.getresponse.return_value = mock_response

        with patch("cp.cli.create_config.http.client.HTTPConnection", return_value=mock_conn):
            with pytest.raises(RuntimeError, match="não-JSON"):
                cc._http_request("GET", "http://host:80/api")

    def test_https_usa_https_connection(self) -> None:
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"ok": true}'
        mock_conn.getresponse.return_value = mock_response

        with patch("cp.cli.create_config.http.client.HTTPSConnection", return_value=mock_conn):
            status, data = cc._http_request("GET", "https://host:443/api")

        assert status == 200
        assert data == {"ok": True}


# ---------------------------------------------------------------------------
# get_auth_user_data — erro de rede
# ---------------------------------------------------------------------------


class TestGetAuthUserDataErroRede:
    def test_erro_de_rede_levanta_runtime_error(self) -> None:
        with patch.object(cc, "_http_request", side_effect=RuntimeError("timeout")):
            with pytest.raises(RuntimeError, match="Erro ao buscar dados"):
                cc.get_auth_user_data("http://auth:3010", "tok", "uuid")


class TestWriteConfigEnv:
    def test_cria_arquivo_com_todas_as_variáveis(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
            operator_uuid="uuid-123",
            operator_login="op.login",
            operator_nome="Operador",
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

    def test_cria_diretório_server_se_não_existir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
            operator_uuid="uuid-x",
            operator_login="login",
            operator_nome="Nome",
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


_FAKE_USER_DATA = {
    "uuid": "uuid-operador-123",
    "login": "operador.teste",
    "nome": "Operador Teste",
    "tipo_posto_grad_id": 1,
    "tipo_turno_id": 2,
}


class TestLoginAuthServer:
    def test_login_bem_sucedido_retorna_token_e_uuid(self) -> None:
        status = 201
        body = {
            "success": True,
            "dados": {"token": "tok123", "uuid": "uuid-abc"},
        }
        with patch.object(cc, "_http_request", return_value=(status, body)):
            token, uuid = cc.login_auth_server("http://auth:3010", "user", "pass")
        assert token == "tok123"
        assert uuid == "uuid-abc"

    def test_credenciais_invalidas_levanta_runtime_error(self) -> None:
        with patch.object(cc, "_http_request", return_value=(401, {"success": False})):
            with pytest.raises(RuntimeError, match="Login no Serviço de Autenticação falhou"):
                cc.login_auth_server("http://auth:3010", "user", "errada")

    def test_falha_de_rede_levanta_runtime_error(self) -> None:
        with patch.object(cc, "_http_request", side_effect=RuntimeError("timeout")):
            with pytest.raises(RuntimeError, match="Erro ao se comunicar"):
                cc.login_auth_server("http://auth:3010", "user", "pass")


class TestGetAuthUserData:
    def test_busca_dados_com_sucesso(self) -> None:
        body = {"dados": _FAKE_USER_DATA}
        with patch.object(cc, "_http_request", return_value=(200, body)):
            data = cc.get_auth_user_data("http://auth:3010", "tok123", "uuid-abc")
        assert data["login"] == "operador.teste"
        assert data["nome"] == "Operador Teste"
        assert data["uuid"] == "uuid-operador-123"

    def test_status_nao_200_levanta_runtime_error(self) -> None:
        with patch.object(cc, "_http_request", return_value=(403, {})):
            with pytest.raises(RuntimeError, match="HTTP 403"):
                cc.get_auth_user_data("http://auth:3010", "tok123", "uuid-abc")

    def test_dados_ausentes_levanta_runtime_error(self) -> None:
        with patch.object(cc, "_http_request", return_value=(200, {"outro": "campo"})):
            with pytest.raises(RuntimeError, match="HTTP 200"):
                cc.get_auth_user_data("http://auth:3010", "tok123", "uuid-abc")


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
            "auth_user": "operador",
            "auth_password": "senha123",
            "app_port": "8000",
            "log_level": "INFO",
            "overwrite": overwrite,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def _mock_auth(self) -> tuple[object, object, object]:
        """Retorna mocks prontos para verify_auth_server, login e get_user."""
        return (
            patch.object(cc, "verify_auth_server"),
            patch.object(cc, "login_auth_server", return_value=("tok123", "uuid-operador-123")),
            patch.object(cc, "get_auth_user_data", return_value=_FAKE_USER_DATA),
        )

    def test_fluxo_completo_grava_config_env(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        args = self._make_args()
        m_verify, m_login, m_user = self._mock_auth()

        with patch.object(cc, "verify_sap_connection"), m_verify, m_login, m_user:
            cc.create_config(args)

        content = (server_dir / "config.env").read_text()
        assert "JWT_SECRET=" in content
        jwt_line = next(line for line in content.splitlines() if line.startswith("JWT_SECRET="))
        jwt_value = jwt_line.split("=", 1)[1]
        assert len(jwt_value) == 128
        assert all(c in "0123456789abcdef" for c in jwt_value)
        assert "AUTH_SERVER=http://auth:3010" in content
        assert "OPERATOR_UUID=uuid-operador-123" in content
        assert "OPERATOR_LOGIN=operador.teste" in content
        assert "OPERATOR_NOME=Operador Teste" in content

    def test_config_env_existente_sem_overwrite_termina_com_exit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        existing = server_dir / "config.env"
        existing.write_text("existente", encoding="utf-8")

        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", existing)

        args = self._make_args()

        with pytest.raises(SystemExit) as exc_info:
            cc.create_config(args)
        assert exc_info.value.code == 1

    def test_config_env_existente_com_overwrite_sobrescreve(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        server_dir.mkdir()
        existing = server_dir / "config.env"
        existing.write_text("conteudo_antigo", encoding="utf-8")

        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", existing)

        args = self._make_args(overwrite=True)
        m_verify, m_login, m_user = self._mock_auth()

        with patch.object(cc, "verify_sap_connection"), m_verify, m_login, m_user:
            cc.create_config(args)

        content = existing.read_text()
        assert "conteudo_antigo" not in content
        assert "JWT_SECRET=" in content

    def test_falha_na_conexao_sap_termina_com_exit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        args = self._make_args()

        with patch.object(cc, "verify_sap_connection", side_effect=RuntimeError("conexão recusada")):
            with pytest.raises(SystemExit) as exc_info:
                cc.create_config(args)
        assert exc_info.value.code == 1

    def test_falha_no_auth_server_termina_com_exit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        args = self._make_args()

        with (
            patch.object(cc, "verify_sap_connection"),
            patch.object(cc, "verify_auth_server", side_effect=RuntimeError("auth offline")),
        ):
            with pytest.raises(SystemExit) as exc_info:
                cc.create_config(args)
        assert exc_info.value.code == 1

    def test_falha_no_login_termina_com_exit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        server_dir = tmp_path / "server"
        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        args = self._make_args()

        with (
            patch.object(cc, "verify_sap_connection"),
            patch.object(cc, "verify_auth_server"),
            patch.object(cc, "login_auth_server", side_effect=RuntimeError("credenciais inválidas")),
        ):
            with pytest.raises(SystemExit) as exc_info:
                cc.create_config(args)
        assert exc_info.value.code == 1

    def test_auth_url_tem_barra_final_removida(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """URL com barra final deve ser normalizada antes de gravar."""
        server_dir = tmp_path / "server"
        monkeypatch.setattr(cc, "_SERVER_DIR", server_dir)
        monkeypatch.setattr(cc, "_CONFIG_ENV", server_dir / "config.env")

        args = self._make_args(auth_server_url="http://auth:3010/")
        m_verify, m_login, m_user = self._mock_auth()

        with patch.object(cc, "verify_sap_connection"), m_verify, m_login, m_user:
            cc.create_config(args)

        content = (server_dir / "config.env").read_text()
        assert "AUTH_SERVER=http://auth:3010\n" in content
        assert "AUTH_SERVER=http://auth:3010/" not in content
