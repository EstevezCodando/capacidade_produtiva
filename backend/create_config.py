"""
Bootstrap CLI do CapacidadeProdutiva.

Responsabilidades:
  1. Coletar credenciais do SAP e do Serviço de Autenticação
     (interativamente ou via flags de linha de comando).
  2. Validar conectividade com o banco do SAP (read-only).
  3. Validar que o Serviço de Autenticação está acessível.
  4. Ler o JWT_SECRET do config.env do SAP (nunca gera um novo).
  5. Gravar server/config.env com todas as variáveis necessárias.

Não cria bancos de dados — ações privilegiadas são opt-in explícito.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_SERVER_DIR = _HERE / "server"
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
    """Verifica conexão read-only com o banco do SAP (sem imports de nível de módulo)."""
    try:
        import psycopg2  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "psycopg2-binary não está instalado. Execute: uv add psycopg2-binary"
        ) from exc

    dsn = (
        f"host={host} port={port} dbname={dbname} "
        f"user={user} password={password} connect_timeout=10"
    )
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
    import http.client
    import json
    import ssl
    from urllib.parse import urlparse

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
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                host, port, timeout=10, context=ctx
            )
        else:
            conn = http.client.HTTPConnection(host, port, timeout=10)

        conn.request("GET", "/api")
        response = conn.getresponse()
        body = response.read().decode()
        conn.close()
    except OSError as exc:
        raise RuntimeError(
            f"Erro ao se comunicar com o Serviço de Autenticação ({url}): {exc}"
        ) from exc

    if response.status != 200:
        raise RuntimeError(
            f"Serviço de Autenticação retornou HTTP {response.status} em GET /api"
        )

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Serviço de Autenticação retornou resposta não-JSON em GET /api"
        ) from exc

    expected_message = "Serviço de autenticação operacional"
    if data.get("message") != expected_message:
        raise RuntimeError(
            f"Resposta inesperada do Serviço de Autenticação: {data}"
        )


# ---------------------------------------------------------------------------
# Leitura do JWT_SECRET do SAP
# ---------------------------------------------------------------------------


def read_jwt_secret_from_sap_config(sap_config_env_path: Path) -> str:
    """
    Lê o JWT_SECRET do config.env do SAP.

    O CapacidadeProdutiva reutiliza o mesmo secret para compatibilidade
    com os tokens emitidos pelo Serviço de Autenticação.
    """
    if not sap_config_env_path.exists():
        raise FileNotFoundError(
            f"Arquivo config.env do SAP não encontrado: {sap_config_env_path}\n"
            "Informe o caminho correto com --sap-config-env."
        )

    for line in sap_config_env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("JWT_SECRET="):
            secret = line.split("=", 1)[1].strip()
            if not secret:
                raise ValueError(
                    f"JWT_SECRET está vazio no arquivo {sap_config_env_path}"
                )
            return secret

    raise KeyError(
        f"JWT_SECRET não encontrado no arquivo {sap_config_env_path}"
    )


# ---------------------------------------------------------------------------
# Gravação do config.env
# ---------------------------------------------------------------------------


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
    params["cp_db_host"] = args.cp_db_host or _ask(
        "Endereço do servidor PostgreSQL do CP", default="localhost"
    )
    params["cp_db_port"] = int(
        args.cp_db_port or _ask("Porta PostgreSQL do CP", default="5432")
    )
    params["cp_db_name"] = args.cp_db_name or _ask(
        "Nome do banco de dados do CP", default="capacidade_produtiva"
    )
    params["cp_db_user"] = args.cp_db_user or _ask("Usuário PostgreSQL do CP")
    params["cp_db_password"] = args.cp_db_password or _ask(
        "Senha do usuário PostgreSQL do CP", secret=True
    )

    # -- Banco SAP ----------------------------------------------------------
    print()
    print("--- Banco de dados SAP (somente leitura) ---")
    params["sap_db_host"] = args.sap_db_host or _ask(
        "Endereço do servidor PostgreSQL do SAP", default="localhost"
    )
    params["sap_db_port"] = int(
        args.sap_db_port or _ask("Porta PostgreSQL do SAP", default="5432")
    )
    params["sap_db_name"] = args.sap_db_name or _ask(
        "Nome do banco de dados do SAP", default="sap"
    )
    params["sap_db_user"] = args.sap_db_user or _ask("Usuário PostgreSQL do SAP (somente leitura)")
    params["sap_db_password"] = args.sap_db_password or _ask(
        "Senha do usuário PostgreSQL do SAP", secret=True
    )

    # -- Serviço de Autenticação --------------------------------------------
    print()
    print("--- Serviço de Autenticação ---")
    params["auth_server_url"] = args.auth_server_url or _ask(
        "URL do Serviço de Autenticação (ex: http://192.168.0.10:3010)"
    )

    # -- config.env do SAP (para extrair JWT_SECRET) -----------------------
    print()
    print("--- JWT Secret (reaproveitado do SAP) ---")
    params["sap_config_env_path"] = Path(
        args.sap_config_env
        or _ask(
            "Caminho completo para o config.env do SAP",
            default="/opt/sap/server/config.env",
        )
    )

    # -- Aplicação ----------------------------------------------------------
    print()
    print("--- Configuração da aplicação ---")
    params["app_port"] = int(
        args.app_port or _ask("Porta do servidor CapacidadeProdutiva", default="8000")
    )
    params["log_level"] = args.log_level or _ask(
        "Nível de log (DEBUG/INFO/WARNING/ERROR)", default="INFO"
    )

    return params


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------


def create_config(args: argparse.Namespace) -> None:
    """Executa o fluxo completo de configuração."""
    try:
        # Verificar se config.env já existe
        if _CONFIG_ENV.exists() and not args.overwrite:
            raise FileExistsError(
                f"Arquivo {_CONFIG_ENV} já existe. "
                "Use --overwrite para sobrescrever."
            )

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

        # 2. Validar Serviço de Autenticação
        _print_ok("Validando Serviço de Autenticação...")
        auth_url: str = params["auth_server_url"]
        auth_url = auth_url.rstrip("/")
        verify_auth_server(auth_url)
        _print_ok("  ✓ Serviço de Autenticação OK")

        # 3. Ler JWT_SECRET do SAP
        _print_ok("Lendo JWT_SECRET do config.env do SAP...")
        jwt_secret = read_jwt_secret_from_sap_config(params["sap_config_env_path"])
        _print_ok("  ✓ JWT_SECRET lido com sucesso")

        # 4. Gravar config.env
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
        )
        _print_ok(f"  ✓ {_CONFIG_ENV} criado com sucesso")

        print()
        _print_ok("Configuração concluída.")
        _print_ok("Próximo passo: uv run alembic upgrade head")

    except (FileExistsError, FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        _print_err(f"\nErro: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
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

    # SAP config.env para extrair JWT_SECRET
    parser.add_argument(
        "--sap-config-env",
        help="Caminho para o config.env do SAP (para extrair JWT_SECRET)",
    )

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

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    create_config(args)
