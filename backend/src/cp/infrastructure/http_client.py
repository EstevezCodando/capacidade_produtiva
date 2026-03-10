"""Cliente HTTP para comunicação com servico_autenticacao.

Módulo utilitário que encapsula chamadas HTTP/HTTPS para o serviço de
autenticação. Não depende de bibliotecas externas além da stdlib.

Características:
    - Suporte a HTTP e HTTPS
    - SSL configurável (desabilita verificação para ambientes de dev)
    - Timeout configurável
    - Retorna tupla (status, json_body) para facilitar tratamento de erros

Uso:
    from cp.infrastructure.http_client import http_get, http_post

    status, data = http_get("http://auth-server/api")
    status, data = http_post("http://auth-server/api/login", {"usuario": "x", "senha": "y"})
"""

from __future__ import annotations

import http.client
import json
import ssl
from typing import Any
from urllib.parse import urlparse

# Timeout padrão em segundos
_DEFAULT_TIMEOUT = 10

# Contexto SSL permissivo para ambientes de desenvolvimento
# Em produção, considerar usar certificados válidos
_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE


def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, Any]]:
    """Executa requisição GET e retorna (status, json_body).

    Args:
        url: URL completa (ex: http://localhost:3010/api)
        headers: headers adicionais (ex: {"Authorization": "Bearer ..."})
        timeout: timeout em segundos

    Returns:
        Tupla (status_code, json_body).

    Raises:
        OSError: erro de rede/conexão
        json.JSONDecodeError: resposta não é JSON válido
    """
    return _request("GET", url, body=None, headers=headers, timeout=timeout)


def http_post(
    url: str,
    data: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, Any]]:
    """Executa requisição POST com body JSON e retorna (status, json_body).

    Args:
        url: URL completa (ex: http://localhost:3010/api/login)
        data: dicionário a ser enviado como JSON
        headers: headers adicionais
        timeout: timeout em segundos

    Returns:
        Tupla (status_code, json_body).

    Raises:
        OSError: erro de rede/conexão
        json.JSONDecodeError: resposta não é JSON válido
    """
    body = json.dumps(data)
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    return _request("POST", url, body=body, headers=default_headers, timeout=timeout)


def _request(
    method: str,
    url: str,
    body: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, Any]]:
    """Executa requisição HTTP genérica.

    Suporta HTTP e HTTPS automaticamente baseado no scheme da URL.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme não suportado: {parsed.scheme}")

    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    if parsed.scheme == "https":
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(host, port, timeout=timeout, context=_SSL_CONTEXT)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)

    try:
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        raw_body = response.read().decode("utf-8")
        status = response.status
    finally:
        conn.close()

    # Tenta parsear como JSON
    try:
        data = json.loads(raw_body) if raw_body.strip() else {}
    except json.JSONDecodeError:
        # Se não for JSON, retorna como erro genérico
        data = {"raw": raw_body[:500]}

    return status, data
