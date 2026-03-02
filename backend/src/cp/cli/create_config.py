"""
Bootstrap CLI do CapacidadeProdutiva.

Responsabilidades:
  1. Coletar credenciais do SAP e do Serviço de Autenticação
     (interativamente ou via flags de linha de comando).
  2. Validar conectividade com o banco do SAP (read-only).
  3. Validar que o Serviço de Autenticação está acessível.
  4. Validar login do operador no Serviço de Autenticação.
  5. Buscar e gravar dados do operador (uuid, login, nome) no config.env.
  6. Gerar JWT_SECRET criptograficamente seguro.
  7. Gravar server/config.env com todas as variáveis necessárias.

Criação do banco e schemas é responsabilidade do Alembic (alembic upgrade head).
"""

import argparse
import getpass
import http.client
import json
import secrets
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psycopg2

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------

# O arquivo está em src/cp/cli/create_config.py.
# backend/ é 4 níveis acima: cli/ → cp/ → src/ → backend/
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
_SERVER_DIR = _BACKEND_DIR / "server"
_CONFIG_ENV = _SERVER_DIR / "config.env"


# ---------------------------------------------------------------------------
# Helpers de I/O
# ---------------------------------------------------------------------------


def _print_ok(msg: str) -> None:
    print(f"\033[94m{msg}\033[0m")  # azul


def _print_err(msg: str) -> None:
    print(f"\033[91m{msg}\033[0m", file=sys.stderr)  # vermelho


def _ask(prompt: str, default: str | None = None, secret: bool = False) -> str:
    """Solicita input do usuário; usa default se Enter for pressionado."""
    display_prompt = f"{prompt}"
    if default is not None:
        display_prompt += f" [{default}]"
    display_prompt += ": "

    if secret:
        value = getpass.getpass(display_prompt)
    else:
        value = input(display_prompt).strip()

    if not value:
        if default is not None:
            return default
        raise ValueError(f"Campo obrigatório não informado: {prompt}")
    return value


# ---------------------------------------------------------------------------
# Verificações de conectividade
# ---------------------------------------------------------------------------


def verify_sap_connection(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
) -> None:
    """Verifica conexão read-only com o banco do SAP."""
    dsn = f"host={host} port={port} dbname={dbname} " f"user={user} password={password} connect_timeout=10"
    try:
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
    except psycopg2.OperationalError as exc:
        raise RuntimeError(f"Falha ao conectar no banco SAP: {exc}") from exc


def verify_auth_server(url: str) -> None:
    """Verifica que o Serviço de Autenticação está operacional."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL do Serviço de Autenticação deve iniciar com http:// ou https://")

    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    use_ssl = parsed.scheme == "https"

    try:
        if use_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(host, port, timeout=10, context=ctx)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=10)

        conn.request("GET", "/api")
        response = conn.getresponse()
        body = response.read().decode()
        conn.close()
    except OSError as exc:
        raise RuntimeError(f"Erro ao se comunicar com o Serviço de Autenticação ({url}): {exc}") from exc

    if response.status != 200:
        raise RuntimeError(f"Serviço de Autenticação retornou HTTP {response.status} em GET /api")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Serviço de Autenticação retornou resposta não-JSON em GET /api") from exc

    expected_message = "Serviço de autenticação operacional"
    if data.get("message") != expected_message:
        raise RuntimeError(f"Resposta inesperada do Serviço de Autenticação: {data}")


def _http_request(
    method: str,
    url: str,
    body: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Executa uma requisição HTTP/HTTPS e retorna (status, json_body)."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        if parsed.scheme == "https":
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(host, port, timeout=10, context=ctx)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=10)

        conn.request(
            method,
            parsed.path or "/",
            body=body,
            headers=headers or {},
        )
        response = conn.getresponse()
        raw = response.read().decode()
        status = response.status
        conn.close()
    except OSError as exc:
        raise RuntimeError(f"Erro de rede ao contactar {url}: {exc}") from exc

    try:
        data = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"Resposta não-JSON de {url}: {raw[:200]}") from exc

    return status, data


def login_auth_server(
    url: str,
    usuario: str,
    senha: str,
) -> tuple[str, str]:
    """
    Autentica o operador no Serviço de Autenticação.

    Espelha verifyLoginAuthServer do create_config.js do SAP.
    Retorna (token, uuid) em caso de sucesso.
    """
    endpoint = f"{url}/api/login"
    body = json.dumps({"usuario": usuario, "senha": senha, "aplicacao": "sap"})
    headers = {"Content-Type": "application/json"}

    try:
        status, data = _http_request("POST", endpoint, body=body, headers=headers)
    except RuntimeError as exc:
        raise RuntimeError(f"Erro ao se comunicar com o Serviço de Autenticação: {exc}") from exc

    if status != 201 or not data.get("success") or "dados" not in data or "token" not in data["dados"] or "uuid" not in data["dados"]:
        raise RuntimeError("Login no Serviço de Autenticação falhou. " "Verifique usuário e senha.")

    return data["dados"]["token"], data["dados"]["uuid"]


def get_auth_user_data(url: str, token: str, uuid: str) -> dict[str, Any]:
    """
    Busca os dados do operador autenticado.

    Espelha getAuthUserData do create_config.js do SAP.
    Retorna os dados do usuário (login, nome, uuid, etc).
    """
    endpoint = f"{url}/api/usuarios/{uuid}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    try:
        status, data = _http_request("GET", endpoint, headers=headers)
    except RuntimeError as exc:
        raise RuntimeError(f"Erro ao buscar dados do usuário no Serviço de Autenticação: {exc}") from exc

    if status != 200 or "dados" not in data:
        raise RuntimeError(f"Não foi possível obter dados do usuário (HTTP {status}).")

    return dict(data["dados"])


# ---------------------------------------------------------------------------
# JWT Secret
# ---------------------------------------------------------------------------


def generate_jwt_secret() -> str:
    """
    Gera um JWT_SECRET criptograficamente seguro de 64 bytes (128 hex chars).
    Equivalente ao crypto.randomBytes(64).toString('hex') do SAP.
    """
    return secrets.token_hex(64)


def write_config_env(
    *,
    cp_db_host: str,
    cp_db_port: int,
    cp_db_name: str,
    cp_db_user: str,
    cp_db_password: str,
    sap_db_host: str,
    sap_db_port: int,
    sap_db_name: str,
    sap_db_user: str,
    sap_db_password: str,
    auth_server_url: str,
    jwt_secret: str,
    app_port: int,
    log_level: str,
    operator_uuid: str,
    operator_login: str,
    operator_nome: str,
) -> None:
    """Grava server/config.env com todas as variáveis de configuração."""
    _SERVER_DIR.mkdir(parents=True, exist_ok=True)

    content = f"""\
# Gerado automaticamente por create_config.py
# NÃO comitar este arquivo — ele contém credenciais.

# ---------------------------------------------------------------------------
# Aplicação CapacidadeProdutiva
# ---------------------------------------------------------------------------
APP_PORT={app_port}
LOG_LEVEL={log_level}

# ---------------------------------------------------------------------------
# Banco de dados auxiliar (CapacidadeProdutiva)
# ---------------------------------------------------------------------------
CP_DB_HOST={cp_db_host}
CP_DB_PORT={cp_db_port}
CP_DB_NAME={cp_db_name}
CP_DB_USER={cp_db_user}
CP_DB_PASSWORD={cp_db_password}

# ---------------------------------------------------------------------------
# Banco de dados SAP (somente leitura)
# ---------------------------------------------------------------------------
SAP_DB_HOST={sap_db_host}
SAP_DB_PORT={sap_db_port}
SAP_DB_NAME={sap_db_name}
SAP_DB_USER={sap_db_user}
SAP_DB_PASSWORD={sap_db_password}

# ---------------------------------------------------------------------------
# Serviço de Autenticação
# ---------------------------------------------------------------------------
AUTH_SERVER={auth_server_url}

# ---------------------------------------------------------------------------
# Operador — dados gravados na configuração inicial (via Serviço de Autenticação)
# ---------------------------------------------------------------------------
OPERATOR_UUID={operator_uuid}
OPERATOR_LOGIN={operator_login}
OPERATOR_NOME={operator_nome}

# ---------------------------------------------------------------------------
# Segurança — JWT_SECRET reaproveitado do SAP (nunca gerar novo)
# ---------------------------------------------------------------------------
JWT_SECRET={jwt_secret}
"""
    _CONFIG_ENV.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Coleta interativa de parâmetros
# ---------------------------------------------------------------------------


def _collect_from_user(args: argparse.Namespace) -> dict[str, Any]:
    """Solicita ao usuário os valores não fornecidos via flags."""
    params: dict[str, Any] = {}

    print()
    _print_ok("=== CapacidadeProdutiva — Configuração inicial ===")
    print()

    # -- Banco CP -----------------------------------------------------------
    print("--- Banco de dados CapacidadeProdutiva (banco auxiliar) ---")
    params["cp_db_host"] = args.cp_db_host or _ask("Endereço do servidor PostgreSQL do CP", default="localhost")
    params["cp_db_port"] = int(args.cp_db_port or _ask("Porta PostgreSQL do CP", default="5432"))
    params["cp_db_name"] = args.cp_db_name or _ask("Nome do banco de dados do CP", default="capacidade_produtiva")
    params["cp_db_user"] = args.cp_db_user or _ask("Usuário PostgreSQL do CP")
    params["cp_db_password"] = args.cp_db_password or _ask("Senha do usuário PostgreSQL do CP", secret=True)

    # -- Banco SAP ----------------------------------------------------------
    print()
    print("--- Banco de dados SAP (somente leitura) ---")
    params["sap_db_host"] = args.sap_db_host or _ask("Endereço do servidor PostgreSQL do SAP", default="localhost")
    params["sap_db_port"] = int(args.sap_db_port or _ask("Porta PostgreSQL do SAP", default="5432"))
    params["sap_db_name"] = args.sap_db_name or _ask("Nome do banco de dados do SAP", default="sap")
    params["sap_db_user"] = args.sap_db_user or _ask("Usuário PostgreSQL do SAP (somente leitura)")
    params["sap_db_password"] = args.sap_db_password or _ask("Senha do usuário PostgreSQL do SAP", secret=True)

    # -- Serviço de Autenticação --------------------------------------------
    print()
    print("--- Serviço de Autenticação ---")
    params["auth_server_url"] = args.auth_server_url or _ask("URL do Serviço de Autenticação (ex: http://192.168.0.10:3010)")
    params["auth_user"] = args.auth_user or _ask("Usuário do Serviço de Autenticação")
    params["auth_password"] = args.auth_password or _ask("Senha do Serviço de Autenticação", secret=True)

    # -- Aplicação ----------------------------------------------------------
    print()
    print("--- Configuração da aplicação ---")
    params["app_port"] = int(args.app_port or _ask("Porta do servidor CapacidadeProdutiva", default="8000"))
    params["log_level"] = args.log_level or _ask("Nível de log (DEBUG/INFO/WARNING/ERROR)", default="INFO")

    return params


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------


def create_config(args: argparse.Namespace) -> None:
    """Executa o fluxo completo de configuração."""
    try:
        # Verificar se config.env já existe
        if _CONFIG_ENV.exists() and not args.overwrite:
            raise FileExistsError(f"Arquivo {_CONFIG_ENV} já existe. " "Use --overwrite para sobrescrever.")

        params = _collect_from_user(args)

        # 1. Validar conexão SAP
        print()
        _print_ok("Validando conexão com o banco SAP...")
        verify_sap_connection(
            host=params["sap_db_host"],
            port=params["sap_db_port"],
            dbname=params["sap_db_name"],
            user=params["sap_db_user"],
            password=params["sap_db_password"],
        )
        _print_ok("  ✓ Conexão SAP OK")

        # 2. Validar Serviço de Autenticação + login do operador
        _print_ok("Validando Serviço de Autenticação...")
        auth_url: str = params["auth_server_url"]
        auth_url = auth_url.rstrip("/")
        verify_auth_server(auth_url)
        _print_ok("  ✓ Serviço de Autenticação no ar")

        _print_ok("Validando credenciais do operador...")
        token, uuid = login_auth_server(
            auth_url,
            usuario=params["auth_user"],
            senha=params["auth_password"],
        )
        _print_ok("  ✓ Login OK")

        _print_ok("Buscando dados do operador...")
        user_data = get_auth_user_data(auth_url, token, uuid)
        operator_login = str(user_data.get("login", ""))
        operator_nome = str(user_data.get("nome", ""))
        _print_ok(f"  ✓ Operador identificado: {operator_nome} ({operator_login})")

        # 3. Gerar JWT_SECRET
        jwt_secret = generate_jwt_secret()
        _print_ok("  ✓ JWT_SECRET gerado")

        # 5. Gravar config.env
        _print_ok("Gravando server/config.env...")
        write_config_env(
            cp_db_host=params["cp_db_host"],
            cp_db_port=params["cp_db_port"],
            cp_db_name=params["cp_db_name"],
            cp_db_user=params["cp_db_user"],
            cp_db_password=params["cp_db_password"],
            sap_db_host=params["sap_db_host"],
            sap_db_port=params["sap_db_port"],
            sap_db_name=params["sap_db_name"],
            sap_db_user=params["sap_db_user"],
            sap_db_password=params["sap_db_password"],
            auth_server_url=auth_url,
            jwt_secret=jwt_secret,
            app_port=params["app_port"],
            log_level=params["log_level"],
            operator_uuid=uuid,
            operator_login=operator_login,
            operator_nome=operator_nome,
        )
        _print_ok(f"  ✓ {_CONFIG_ENV} criado com sucesso")

        print()
        _print_ok("Configuração concluída.")
        _print_ok("Próximo passo: uv run alembic upgrade head")

    except (FileExistsError, FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        _print_err(f"\nErro: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:  # pragma: no cover
        print("\nCancelado pelo usuário.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="create_config",
        description="Bootstrap de configuração do CapacidadeProdutiva.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Banco CP
    parser.add_argument("--cp-db-host", help="Host do banco CP")
    parser.add_argument("--cp-db-port", help="Porta do banco CP")
    parser.add_argument("--cp-db-name", help="Nome do banco CP")
    parser.add_argument("--cp-db-user", help="Usuário do banco CP")
    parser.add_argument("--cp-db-password", help="Senha do banco CP")

    # Banco SAP
    parser.add_argument("--sap-db-host", help="Host do banco SAP")
    parser.add_argument("--sap-db-port", help="Porta do banco SAP")
    parser.add_argument("--sap-db-name", help="Nome do banco SAP")
    parser.add_argument("--sap-db-user", help="Usuário do banco SAP (somente leitura)")
    parser.add_argument("--sap-db-password", help="Senha do banco SAP")

    # Auth
    parser.add_argument("--auth-server-url", help="URL do Serviço de Autenticação")
    parser.add_argument("--auth-user", help="Usuário do Serviço de Autenticação")
    parser.add_argument("--auth-password", help="Senha do Serviço de Autenticação")

    # App
    parser.add_argument("--app-port", help="Porta da aplicação CP", default=None)
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de log",
        default=None,
    )

    # Comportamento
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescrever server/config.env se já existir",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover
    """Entry point declarado em pyproject.toml [project.scripts]."""
    parser = _build_parser()
    args = parser.parse_args()
    create_config(args)


if __name__ == "__main__":
    main()
