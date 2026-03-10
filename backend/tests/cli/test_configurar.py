# caminho: backend/tests/cli/test_configurar.py
"""Testes do módulo de configuração inicial.

Testa as funções auxiliares do configurar.py sem fazer chamadas de rede reais.
Usa mocks para simular respostas do servico_autenticacao e do banco de dados.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cp.cli import configurar

# ---------------------------------------------------------------------------
# Testes de funções auxiliares de input
# ---------------------------------------------------------------------------


class TestPerguntarTexto:
    """Testes da função _perguntar_texto."""

    def test_retorna_valor_digitado(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "valor_digitado")
        resultado = configurar._perguntar_texto("Pergunta?")
        assert resultado == "valor_digitado"

    def test_retorna_default_quando_vazio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "")
        resultado = configurar._perguntar_texto("Pergunta?", default="padrao")
        assert resultado == "padrao"

    def test_repete_quando_vazio_sem_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        respostas = iter(["", "", "valor_final"])
        monkeypatch.setattr("builtins.input", lambda _: next(respostas))
        resultado = configurar._perguntar_texto("Pergunta?")
        assert resultado == "valor_final"


class TestPerguntarInt:
    """Testes da função _perguntar_int."""

    def test_retorna_inteiro(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "42")
        resultado = configurar._perguntar_int("Numero?")
        assert resultado == 42

    def test_retorna_default_quando_vazio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "")
        resultado = configurar._perguntar_int("Numero?", default=5432)
        assert resultado == 5432

    def test_repete_quando_invalido(self, monkeypatch: pytest.MonkeyPatch) -> None:
        respostas = iter(["abc", "12.5", "100"])
        monkeypatch.setattr("builtins.input", lambda _: next(respostas))
        resultado = configurar._perguntar_int("Numero?")
        assert resultado == 100


class TestPerguntarSimNao:
    """Testes da função _perguntar_sim_nao."""

    @pytest.mark.parametrize("entrada", ["s", "S", "sim", "SIM", "y", "yes"])
    def test_retorna_true_para_sim(self, entrada: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: entrada)
        assert configurar._perguntar_sim_nao("Confirma?") is True

    @pytest.mark.parametrize("entrada", ["n", "N", "nao", "NAO", "não", "no"])
    def test_retorna_false_para_nao(self, entrada: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: entrada)
        assert configurar._perguntar_sim_nao("Confirma?") is False

    def test_retorna_default_true_quando_vazio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert configurar._perguntar_sim_nao("Confirma?", default=True) is True

    def test_retorna_default_false_quando_vazio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert configurar._perguntar_sim_nao("Confirma?", default=False) is False


class TestPerguntarUrlHttp:
    """Testes da função _perguntar_url_http."""

    def test_aceita_url_http(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "http://localhost:3010")
        resultado = configurar._perguntar_url_http("URL?")
        assert resultado == "http://localhost:3010"

    def test_aceita_url_https(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "https://auth.example.com")
        resultado = configurar._perguntar_url_http("URL?")
        assert resultado == "https://auth.example.com"

    def test_remove_barra_final(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _: "http://localhost:3010/")
        resultado = configurar._perguntar_url_http("URL?")
        assert resultado == "http://localhost:3010"

    def test_repete_quando_invalido(self, monkeypatch: pytest.MonkeyPatch) -> None:
        respostas = iter(["localhost", "ftp://server", "http://ok.com"])
        monkeypatch.setattr("builtins.input", lambda _: next(respostas))
        resultado = configurar._perguntar_url_http("URL?")
        assert resultado == "http://ok.com"


# ---------------------------------------------------------------------------
# Testes de geração de secrets
# ---------------------------------------------------------------------------


class TestGerarJwtSecret:
    """Testes da função _gerar_jwt_secret."""

    def test_retorna_string_de_128_chars(self) -> None:
        secret = configurar._gerar_jwt_secret()
        assert len(secret) == 128  # 64 bytes = 128 hex chars

    def test_apenas_caracteres_hex(self) -> None:
        secret = configurar._gerar_jwt_secret()
        assert all(c in "0123456789abcdef" for c in secret)

    def test_gera_valores_diferentes(self) -> None:
        secret1 = configurar._gerar_jwt_secret()
        secret2 = configurar._gerar_jwt_secret()
        assert secret1 != secret2


class TestGerarSecretKey:
    """Testes da função _gerar_secret_key."""

    def test_retorna_string_nao_vazia(self) -> None:
        key = configurar._gerar_secret_key()
        assert len(key) > 0

    def test_gera_valores_diferentes(self) -> None:
        key1 = configurar._gerar_secret_key()
        key2 = configurar._gerar_secret_key()
        assert key1 != key2


# ---------------------------------------------------------------------------
# Testes de verificação do servico_autenticacao
# ---------------------------------------------------------------------------


class TestVerificarServicoAuth:
    """Testes da função _verificar_servico_auth."""

    def test_servidor_operacional_nao_levanta(self) -> None:
        with patch("cp.infrastructure.http_client.http_get") as mock_get:
            mock_get.return_value = (200, {"message": "Serviço de autenticação operacional"})
            # Não deve levantar exceção
            configurar._verificar_servico_auth("http://localhost:3010")

    def test_servidor_retorna_500_levanta_runtime_error(self) -> None:
        with patch("cp.infrastructure.http_client.http_get") as mock_get:
            mock_get.return_value = (500, {"error": "Internal Server Error"})
            with pytest.raises(RuntimeError, match="HTTP 500"):
                configurar._verificar_servico_auth("http://localhost:3010")

    def test_mensagem_errada_levanta_runtime_error(self) -> None:
        with patch("cp.infrastructure.http_client.http_get") as mock_get:
            mock_get.return_value = (200, {"message": "Outro serviço"})
            with pytest.raises(RuntimeError, match="inesperada"):
                configurar._verificar_servico_auth("http://localhost:3010")

    def test_falha_de_rede_levanta_runtime_error(self) -> None:
        with patch("cp.infrastructure.http_client.http_get") as mock_get:
            mock_get.side_effect = OSError("Connection refused")
            with pytest.raises(RuntimeError, match="conectar"):
                configurar._verificar_servico_auth("http://localhost:3010")


# ---------------------------------------------------------------------------
# Testes de autenticação
# ---------------------------------------------------------------------------


class TestAutenticarUsuario:
    """Testes da função _autenticar_usuario."""

    def test_credenciais_validas_retorna_tupla(self) -> None:
        with patch("cp.infrastructure.http_client.http_post") as mock_post:
            mock_post.return_value = (
                201,
                {
                    "success": True,
                    "dados": {
                        "token": "eyJtoken",
                        "uuid": "uuid-123",
                        "administrador": True,
                    },
                },
            )
            token, uuid, admin = configurar._autenticar_usuario("http://localhost:3010", "user", "pass")
            assert token == "eyJtoken"
            assert uuid == "uuid-123"
            assert admin is True

    def test_credenciais_invalidas_levanta_runtime_error(self) -> None:
        with patch("cp.infrastructure.http_client.http_post") as mock_post:
            mock_post.return_value = (400, {"message": "Usuário ou senha inválida"})
            with pytest.raises(RuntimeError, match="Usuário ou senha"):
                configurar._autenticar_usuario("http://localhost:3010", "user", "wrong")

    def test_falha_de_rede_levanta_runtime_error(self) -> None:
        with patch("cp.infrastructure.http_client.http_post") as mock_post:
            mock_post.side_effect = OSError("Connection refused")
            with pytest.raises(RuntimeError, match="conexão"):
                configurar._autenticar_usuario("http://localhost:3010", "user", "pass")

    def test_usa_aplicacao_sap(self) -> None:
        """Verifica que a autenticação usa 'sap' como aplicação."""
        with patch("cp.infrastructure.http_client.http_post") as mock_post:
            mock_post.return_value = (
                201,
                {"success": True, "dados": {"token": "t", "uuid": "u", "administrador": False}},
            )
            configurar._autenticar_usuario("http://localhost:3010", "user", "pass")

            # Verifica o payload enviado
            call_args = mock_post.call_args
            payload = call_args[0][1]  # Segundo argumento posicional
            assert payload["aplicacao"] == "sap"


# ---------------------------------------------------------------------------
# Testes de obter dados do usuário
# ---------------------------------------------------------------------------


class TestObterDadosUsuario:
    """Testes da função _obter_dados_usuario."""

    def test_retorna_dados_do_usuario(self) -> None:
        with patch("cp.infrastructure.http_client.http_get") as mock_get:
            mock_get.return_value = (
                200,
                {
                    "dados": {
                        "uuid": "uuid-123",
                        "login": "operador",
                        "nome": "Operador Teste",
                    }
                },
            )
            dados = configurar._obter_dados_usuario("http://localhost:3010", "token", "uuid-123")
            assert dados["login"] == "operador"
            assert dados["nome"] == "Operador Teste"

    def test_erro_http_levanta_runtime_error(self) -> None:
        with patch("cp.infrastructure.http_client.http_get") as mock_get:
            mock_get.return_value = (401, {"message": "Unauthorized"})
            with pytest.raises(RuntimeError):
                configurar._obter_dados_usuario("http://localhost:3010", "token", "uuid-123")


# ---------------------------------------------------------------------------
# Testes de escrita do config.env
# ---------------------------------------------------------------------------


class TestEscreverConfigEnv:
    """Testes da função _escrever_config_env."""

    def test_grava_variaveis_obrigatorias(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.env"
        configurar._escrever_config_env(
            config_file,
            cp_db_host="localhost",
            cp_db_port=5432,
            cp_db_name="cp",
            cp_db_user="cp_user",
            cp_db_password="cp_pass",
            cp_api_port=3050,
            sap_db_host="localhost",
            sap_db_port=5432,
            sap_db_name="sap",
            sap_db_user="sap_user",
            sap_db_password="sap_pass",
            auth_url="http://localhost:3010",
            auth_admin_user="admin",
            auth_admin_password="admin_pass",
            jwt_secret="jwt_secret_123",
            cp_secret_key="cp_key_456",
            operator_uuid="uuid-op",
            operator_login="operador",
            operator_nome="Operador Teste",
        )

        conteudo = config_file.read_text()
        assert "CP_DB_HOST=localhost" in conteudo
        assert "CP_DB_PORT=5432" in conteudo
        assert "CP_DB_NAME=cp" in conteudo
        assert "SAP_DB_HOST=localhost" in conteudo
        assert "AUTH_URL=http://localhost:3010" in conteudo
        assert "JWT_SECRET=jwt_secret_123" in conteudo
        assert "CP_SECRET_KEY=cp_key_456" in conteudo
        assert "OPERATOR_UUID=uuid-op" in conteudo

    def test_sem_sap_test_nao_inclui_variaveis_test(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.env"
        configurar._escrever_config_env(
            config_file,
            cp_db_host="localhost",
            cp_db_port=5432,
            cp_db_name="cp",
            cp_db_user="cp_user",
            cp_db_password="cp_pass",
            cp_api_port=3050,
            sap_db_host="localhost",
            sap_db_port=5432,
            sap_db_name="sap",
            sap_db_user="sap_user",
            sap_db_password="sap_pass",
            auth_url="http://localhost:3010",
            auth_admin_user="admin",
            auth_admin_password="admin_pass",
            jwt_secret="jwt",
            cp_secret_key="key",
            operator_uuid="uuid",
            operator_login="op",
            operator_nome="Op",
            incluir_sap_test=False,
        )

        conteudo = config_file.read_text()
        assert "SAP_TEST_DB_HOST" not in conteudo

    def test_com_sap_test_inclui_variaveis_test(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.env"
        configurar._escrever_config_env(
            config_file,
            cp_db_host="localhost",
            cp_db_port=5432,
            cp_db_name="cp",
            cp_db_user="cp_user",
            cp_db_password="cp_pass",
            cp_api_port=3050,
            sap_db_host="localhost",
            sap_db_port=5432,
            sap_db_name="sap",
            sap_db_user="sap_user",
            sap_db_password="sap_pass",
            auth_url="http://localhost:3010",
            auth_admin_user="admin",
            auth_admin_password="admin_pass",
            jwt_secret="jwt",
            cp_secret_key="key",
            operator_uuid="uuid",
            operator_login="op",
            operator_nome="Op",
            incluir_sap_test=True,
            sap_test_db_host="test_host",
            sap_test_db_port=5433,
            sap_test_db_name="sap_test",
            sap_test_db_user="test_user",
            sap_test_db_password="test_pass",
        )

        conteudo = config_file.read_text()
        assert "SAP_TEST_DB_HOST=test_host" in conteudo
        assert "SAP_TEST_DB_PORT=5433" in conteudo
        assert "SAP_TEST_DB_NAME=sap_test" in conteudo


# ---------------------------------------------------------------------------
# Testes do fluxo main
# ---------------------------------------------------------------------------


class TestMain:
    """Testes do fluxo principal main()."""

    def test_config_env_existente_sem_overwrite_termina(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Se config.env existe e usuário não quer sobrescrever, sai."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.env").write_text("existente")

        # Usuário responde "n" para sobrescrever
        monkeypatch.setattr("builtins.input", lambda _: "n")

        # Não deve levantar exceção, apenas retornar
        configurar.main()

        # Arquivo não foi modificado
        assert (tmp_path / "config.env").read_text() == "existente"
