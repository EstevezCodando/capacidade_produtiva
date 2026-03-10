# caminho: backend/tests/infrastructure/test_http_client.py
"""Testes do módulo http_client.

Testa as funções de requisição HTTP usando mocks para não fazer chamadas reais.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cp.infrastructure import http_client


class TestHttpGet:
    """Testes da função http_get."""

    def test_retorna_status_e_json(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"key": "value"}'

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            status, data = http_client.http_get("http://localhost:8080/api")

        assert status == 200
        assert data == {"key": "value"}

    def test_usa_https_para_url_https(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPSConnection", return_value=mock_conn) as mock_https:
            http_client.http_get("https://localhost:8080/api")
            mock_https.assert_called_once()

    def test_passa_headers(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            http_client.http_get(
                "http://localhost:8080/api",
                headers={"Authorization": "Bearer token"},
            )
            mock_conn.request.assert_called_once()
            call_args = mock_conn.request.call_args
            assert call_args[1]["headers"]["Authorization"] == "Bearer token"

    def test_retorna_raw_quando_nao_json(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"not json"

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            status, data = http_client.http_get("http://localhost:8080/api")

        assert status == 200
        assert "raw" in data

    def test_levanta_oserror_em_falha_de_conexao(self) -> None:
        with patch("http.client.HTTPConnection") as mock_cls:
            mock_cls.return_value.request.side_effect = OSError("Connection refused")
            with pytest.raises(OSError):
                http_client.http_get("http://localhost:8080/api")


class TestHttpPost:
    """Testes da função http_post."""

    def test_envia_json_no_body(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.read.return_value = b'{"created": true}'

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            status, data = http_client.http_post(
                "http://localhost:8080/api",
                {"usuario": "test", "senha": "pass"},
            )

        assert status == 201
        assert data == {"created": True}

        # Verifica que enviou JSON no body
        call_args = mock_conn.request.call_args
        body_enviado = call_args[1]["body"]
        assert json.loads(body_enviado) == {"usuario": "test", "senha": "pass"}

    def test_define_content_type_json(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            http_client.http_post("http://localhost:8080/api", {})

        call_args = mock_conn.request.call_args
        headers = call_args[1]["headers"]
        assert headers["Content-Type"] == "application/json"

    def test_usa_https_para_url_https(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPSConnection", return_value=mock_conn) as mock_https:
            http_client.http_post("https://localhost:8080/api", {})
            mock_https.assert_called_once()


class TestRequest:
    """Testes da função _request interna."""

    def test_scheme_invalido_levanta_valueerror(self) -> None:
        with pytest.raises(ValueError, match="Scheme não suportado"):
            http_client._request("GET", "ftp://localhost/path")

    def test_inclui_query_string_no_path(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            http_client.http_get("http://localhost:8080/api?param=value")

        call_args = mock_conn.request.call_args
        path = call_args[0][1]  # Segundo argumento posicional
        assert path == "/api?param=value"

    def test_usa_porta_padrao_http(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn) as mock_cls:
            http_client.http_get("http://localhost/api")
            # Porta padrão 80 para HTTP
            mock_cls.assert_called_once()
            call_args = mock_cls.call_args
            assert call_args[0][1] == 80  # Segundo argumento é a porta

    def test_usa_porta_padrao_https(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPSConnection", return_value=mock_conn) as mock_cls:
            http_client.http_get("https://localhost/api")
            # Porta padrão 443 para HTTPS
            mock_cls.assert_called_once()
            call_args = mock_cls.call_args
            assert call_args[0][1] == 443

    def test_fecha_conexao_apos_request(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            http_client.http_get("http://localhost:8080/api")

        mock_conn.close.assert_called_once()

    def test_retorna_dict_vazio_para_body_vazio(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.read.return_value = b""

        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_response

        with patch("http.client.HTTPConnection", return_value=mock_conn):
            status, data = http_client.http_get("http://localhost:8080/api")

        assert status == 204
        assert data == {}
