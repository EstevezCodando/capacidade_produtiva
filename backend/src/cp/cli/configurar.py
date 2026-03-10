"""Configuração inicial do CapacidadeProdutiva.

Este é o ponto de entrada único para configuração do sistema.
Executa um fluxo interativo que:
  1. Coleta credenciais do banco CP e SAP
  2. Valida conectividade com o servico_autenticacao
  3. Autentica o operador administrador
  4. Cria o banco de dados CP (opcional)
  5. Gera secrets de segurança (JWT_SECRET, CP_SECRET_KEY)
  6. Grava config.env com todas as variáveis

Uso:
    uv run configurar

Após a configuração, execute:
    uv run alembic upgrade head   # criar tabelas
    uv run uvicorn cp.main:app    # iniciar servidor
"""

from __future__ import annotations

import secrets
from getpass import getpass
from pathlib import Path

from cp.cli.db import criar_banco_cp


def _print_ok(msg: str) -> None:
    """Imprime mensagem em azul."""
    print(f"\033[94m{msg}\033[0m")


def _print_err(msg: str) -> None:
    """Imprime mensagem em vermelho."""
    print(f"\033[91m{msg}\033[0m")


def _perguntar_texto(pergunta: str, default: str | None = None) -> str:
    """Solicita texto do usuário, com valor default opcional."""
    prompt = f"{pergunta}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "

    while True:
        valor = input(prompt).strip()
        if valor:
            return valor
        if default:
            return default
        print("Valor obrigatório. Tente novamente.")


def _perguntar_int(pergunta: str, default: int | None = None) -> int:
    """Solicita número inteiro do usuário."""
    default_str = str(default) if default else None
    while True:
        valor = _perguntar_texto(pergunta, default_str)
        try:
            return int(valor)
        except ValueError:
            print("Digite um número inteiro válido.")


def _perguntar_sim_nao(pergunta: str, default: bool = True) -> bool:
    """Solicita confirmação sim/não."""
    hint = "S/n" if default else "s/N"
    while True:
        valor = input(f"{pergunta} ({hint}): ").strip().lower()
        if valor == "":
            return default
        if valor in {"s", "sim", "y", "yes"}:
            return True
        if valor in {"n", "nao", "não", "no"}:
            return False
        print("Resposta inválida. Digite s ou n.")


def _perguntar_url_http(pergunta: str) -> str:
    """Solicita URL que deve começar com http:// ou https://."""
    while True:
        valor = _perguntar_texto(pergunta)
        if valor.startswith("http://") or valor.startswith("https://"):
            return valor.rstrip("/")
        print("A URL deve iniciar com http:// ou https://")


def _gerar_jwt_secret() -> str:
    """Gera JWT_SECRET criptograficamente seguro.

    Equivalente a: crypto.randomBytes(64).toString('hex') do SAP.
    """
    return secrets.token_hex(64)


def _gerar_secret_key() -> str:
    """Gera chave interna do CP para sessões e CSRF."""
    return secrets.token_urlsafe(48)


def _verificar_servico_auth(auth_url: str) -> None:
    """Verifica se o servico_autenticacao está operacional."""
    from cp.infrastructure.http_client import http_get

    try:
        status, data = http_get(f"{auth_url}/api")
    except OSError as exc:
        raise RuntimeError(f"Erro ao conectar em {auth_url}: {exc}") from exc

    if status != 200:
        raise RuntimeError(f"servico_autenticacao retornou HTTP {status}")

    if data.get("message") != "Serviço de autenticação operacional":
        raise RuntimeError(f"Resposta inesperada: {data}")


def _autenticar_usuario(auth_url: str, usuario: str, senha: str) -> tuple[str, str, bool]:
    """Autentica usuário no servico_autenticacao.

    Returns:
        Tupla (token, uuid, administrador)

    Nota: Usamos 'sap' como aplicação porque o capacidade_produtiva
    consome dados do SAP e compartilha a mesma base de usuários.
    Para registrar uma aplicação própria, use a interface web do
    servico_autenticacao ou insira diretamente no banco:

        INSERT INTO dgeo.aplicacao (nome, nome_abrev, ativa)
        VALUES ('Capacidade Produtiva', 'capacidade_produtiva', true);
    """
    from cp.infrastructure.http_client import http_post

    # Usa 'sap' como aplicação pois compartilhamos a mesma base de usuários
    # O capacidade_produtiva é um consumidor de dados do SAP
    payload = {
        "usuario": usuario,
        "senha": senha,
        "aplicacao": "sap",  # Aplicação já registrada no servico_autenticacao
    }

    try:
        status, data = http_post(f"{auth_url}/api/login", payload)
    except OSError as exc:
        raise RuntimeError(f"Erro de conexão: {exc}") from exc

    if status != 201:
        msg = data.get("message", "Credenciais inválidas")
        raise RuntimeError(f"Autenticação falhou: {msg}")

    if not data.get("success"):
        raise RuntimeError("Autenticação falhou")

    dados = data.get("dados", {})
    token = dados.get("token", "")
    uuid = dados.get("uuid", "")
    admin = dados.get("administrador", False)

    if not token or not uuid:
        raise RuntimeError("Resposta incompleta do servico_autenticacao")

    return token, uuid, admin


def _obter_dados_usuario(auth_url: str, token: str, uuid: str) -> dict[str, str]:
    """Busca dados completos do usuário autenticado."""
    from cp.infrastructure.http_client import http_get

    headers = {"Authorization": f"Bearer {token}"}

    try:
        status, data = http_get(f"{auth_url}/api/usuarios/{uuid}", headers=headers)
    except OSError as exc:
        raise RuntimeError(f"Erro de conexão: {exc}") from exc

    if status != 200:
        raise RuntimeError(f"Erro ao buscar dados do usuário: HTTP {status}")

    dados: dict[str, str] = data.get("dados", {})
    return dados


def _escrever_config_env(
    caminho: Path,
    *,
    cp_db_host: str,
    cp_db_port: int,
    cp_db_name: str,
    cp_db_user: str,
    cp_db_password: str,
    cp_api_port: int,
    sap_db_host: str,
    sap_db_port: int,
    sap_db_name: str,
    sap_db_user: str,
    sap_db_password: str,
    auth_url: str,
    auth_admin_user: str,
    auth_admin_password: str,
    jwt_secret: str,
    cp_secret_key: str,
    operator_uuid: str,
    operator_login: str,
    operator_nome: str,
    incluir_sap_test: bool = False,
    sap_test_db_host: str = "",
    sap_test_db_port: int = 5432,
    sap_test_db_name: str = "",
    sap_test_db_user: str = "",
    sap_test_db_password: str = "",
) -> None:
    """Grava config.env com todas as variáveis de configuração."""
    conteudo = f"""\
# Gerado automaticamente por `uv run configurar`
# NÃO comitar este arquivo — ele contém credenciais.

# ---------------------------------------------------------------------------
# Ambiente
# ---------------------------------------------------------------------------
ENVIRONMENT=local

# ---------------------------------------------------------------------------
# Aplicação CapacidadeProdutiva
# ---------------------------------------------------------------------------
CP_API_PORT={cp_api_port}
# Chave interna do CP — usada para sessões, CSRF, etc.
CP_SECRET_KEY={cp_secret_key}

# ---------------------------------------------------------------------------
# Banco de dados CapacidadeProdutiva
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
AUTH_URL={auth_url}
AUTH_ADMIN_USER={auth_admin_user}
AUTH_ADMIN_PASSWORD={auth_admin_password}

# ---------------------------------------------------------------------------
# Operador — dados do admin inicial (via servico_autenticacao)
# ---------------------------------------------------------------------------
OPERATOR_UUID={operator_uuid}
OPERATOR_LOGIN={operator_login}
OPERATOR_NOME={operator_nome}

# ---------------------------------------------------------------------------
# Segurança — JWT_SECRET para validação de tokens
# ---------------------------------------------------------------------------
# NOTA: Este secret foi gerado automaticamente.
# Para SSO com o SAP, substitua pelo JWT_SECRET do config.env do SAP.
JWT_SECRET={jwt_secret}
"""

    if incluir_sap_test:
        conteudo += f"""
# ---------------------------------------------------------------------------
# Banco de dados SAP_TEST (desenvolvimento/testes)
# ---------------------------------------------------------------------------
SAP_TEST_DB_HOST={sap_test_db_host}
SAP_TEST_DB_PORT={sap_test_db_port}
SAP_TEST_DB_NAME={sap_test_db_name}
SAP_TEST_DB_USER={sap_test_db_user}
SAP_TEST_DB_PASSWORD={sap_test_db_password}
"""

    caminho.write_text(conteudo, encoding="utf-8")


def main() -> None:
    """Entry point do comando `uv run configurar`."""
    try:
        print()
        _print_ok("=== CapacidadeProdutiva — Configuração inicial ===")
        print()

        # Verificar se config.env já existe
        config_path = Path("config.env")
        if config_path.exists():
            if not _perguntar_sim_nao("config.env já existe. Deseja sobrescrever", default=False):
                print("Cancelado.")
                return

        # --- Banco CP ---
        print("--- Banco de dados CapacidadeProdutiva ---")
        cp_db_host = _perguntar_texto("Endereço do servidor PostgreSQL do CP", "localhost")
        cp_db_port = _perguntar_int("Porta do PostgreSQL do CP", 5432)
        cp_db_name = _perguntar_texto("Nome do banco de dados do CP", "capacidade_produtiva")
        cp_db_user = _perguntar_texto("Usuário PostgreSQL do CP")
        cp_db_password = getpass("Senha do usuário PostgreSQL do CP: ").strip()

        criar_cp = _perguntar_sim_nao("Deseja criar o banco de dados do CP agora")
        if criar_cp:
            admin_user = _perguntar_texto("Usuário admin do PostgreSQL (ex: postgres)", "postgres")
            admin_pass = getpass("Senha do usuário admin: ").strip()
            if criar_banco_cp(cp_db_host, cp_db_port, admin_user, admin_pass, cp_db_name):
                _print_ok(f"  ✓ Banco '{cp_db_name}' criado com sucesso")
            else:
                _print_ok(f"  ℹ Banco '{cp_db_name}' já existe")

        # --- Banco SAP ---
        print()
        print("--- Banco de dados SAP (somente leitura) ---")
        sap_db_host = _perguntar_texto("Endereço do servidor PostgreSQL do SAP", cp_db_host)
        sap_db_port = _perguntar_int("Porta do PostgreSQL do SAP", cp_db_port)
        sap_db_name = _perguntar_texto("Nome do banco de dados do SAP", "sap")
        sap_db_user = _perguntar_texto("Usuário PostgreSQL do SAP (somente leitura)")
        sap_db_password = getpass("Senha do usuário PostgreSQL do SAP: ").strip()

        # --- Serviço de Autenticação ---
        print()
        print("--- Serviço de Autenticação ---")
        auth_url = _perguntar_url_http("URL do servico_autenticacao (ex: http://192.168.0.10:3010)")

        _print_ok("Verificando conectividade...")
        _verificar_servico_auth(auth_url)
        _print_ok("  ✓ servico_autenticacao operacional")

        auth_user = _perguntar_texto("Usuário do servico_autenticacao (será admin do CP)")
        auth_password = getpass("Senha do usuário: ").strip()

        _print_ok("Autenticando...")
        token, uuid, is_admin = _autenticar_usuario(auth_url, auth_user, auth_password)
        _print_ok(f"  ✓ Login OK (admin={is_admin})")

        _print_ok("Buscando dados do operador...")
        user_data = _obter_dados_usuario(auth_url, token, uuid)
        op_login = user_data.get("login", auth_user)
        op_nome = user_data.get("nome", "")
        _print_ok(f"  ✓ Operador: {op_nome} ({op_login})")

        # --- Aplicação ---
        print()
        print("--- Configuração da aplicação ---")
        cp_api_port = _perguntar_int("Porta do servidor CapacidadeProdutiva", 3050)

        # --- SAP_TEST (opcional) ---
        print()
        incluir_sap_test = _perguntar_sim_nao("Incluir configuração de SAP_TEST (desenvolvimento)", default=False)

        sap_test_db_host = ""
        sap_test_db_port = 5432
        sap_test_db_name = ""
        sap_test_db_user = ""
        sap_test_db_password = ""

        if incluir_sap_test:
            print()
            print("--- Banco de dados SAP_TEST ---")
            sap_test_db_host = _perguntar_texto("Endereço do PostgreSQL do SAP_TEST", sap_db_host)
            sap_test_db_port = _perguntar_int("Porta do PostgreSQL do SAP_TEST", sap_db_port)
            sap_test_db_name = _perguntar_texto("Nome do banco SAP_TEST", "sap_test")
            sap_test_db_user = _perguntar_texto("Usuário do SAP_TEST", sap_db_user)
            sap_test_db_password = getpass("Senha do SAP_TEST: ").strip()

        # --- Gerar secrets ---
        _print_ok("Gerando chaves de segurança...")
        jwt_secret = _gerar_jwt_secret()
        cp_secret_key = _gerar_secret_key()
        _print_ok("  ✓ JWT_SECRET gerado (128 caracteres hex)")
        _print_ok("  ✓ CP_SECRET_KEY gerado")

        # --- Gravar config.env ---
        _print_ok("Gravando config.env...")
        _escrever_config_env(
            config_path,
            cp_db_host=cp_db_host,
            cp_db_port=cp_db_port,
            cp_db_name=cp_db_name,
            cp_db_user=cp_db_user,
            cp_db_password=cp_db_password,
            cp_api_port=cp_api_port,
            sap_db_host=sap_db_host,
            sap_db_port=sap_db_port,
            sap_db_name=sap_db_name,
            sap_db_user=sap_db_user,
            sap_db_password=sap_db_password,
            auth_url=auth_url,
            auth_admin_user=auth_user,
            auth_admin_password=auth_password,
            jwt_secret=jwt_secret,
            cp_secret_key=cp_secret_key,
            operator_uuid=uuid,
            operator_login=op_login,
            operator_nome=op_nome,
            incluir_sap_test=incluir_sap_test,
            sap_test_db_host=sap_test_db_host,
            sap_test_db_port=sap_test_db_port,
            sap_test_db_name=sap_test_db_name,
            sap_test_db_user=sap_test_db_user,
            sap_test_db_password=sap_test_db_password,
        )
        _print_ok(f"  ✓ {config_path} criado com sucesso")

        print()
        _print_ok("=" * 60)
        _print_ok("Configuração concluída!")
        _print_ok("")
        _print_ok("Próximos passos:")
        _print_ok("  1. uv run alembic upgrade head   # criar tabelas do CP")
        _print_ok("  2. uv run uvicorn cp.main:app    # iniciar o servidor")
        _print_ok("")
        _print_ok("NOTA sobre SSO com SAP:")
        _print_ok("  Para que tokens do SAP funcionem no CP, copie o")
        _print_ok("  JWT_SECRET do config.env do SAP para o config.env do CP.")
        _print_ok("=" * 60)

    except RuntimeError as exc:
        _print_err(f"\nErro: {exc}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\nCancelado.")
        raise SystemExit(0)
