from __future__ import annotations

from getpass import getpass
from pathlib import Path

from cp.cli.bootstrap_config import ConfigEnv, escrever_config_env
from cp.cli.bootstrap_db import criar_banco_se_necessario


def _perguntar_texto(pergunta: str) -> str:
    while True:
        valor = input(pergunta).strip()
        if valor:
            return valor
        print("Valor obrigatório. Tente novamente.")


def _perguntar_int(pergunta: str) -> int:
    while True:
        valor = _perguntar_texto(pergunta)
        try:
            return int(valor)
        except ValueError:
            print("Digite um número inteiro válido.")


def _perguntar_sim_nao(pergunta: str) -> bool:
    while True:
        valor = input(f"{pergunta} (s/n): ").strip().lower()
        if valor in {"s", "sim"}:
            return True
        if valor in {"n", "nao", "não"}:
            return False
        print("Resposta inválida. Digite s ou n.")


def _perguntar_url_http(pergunta: str) -> str:
    while True:
        valor = _perguntar_texto(pergunta)
        if valor.startswith("http://") or valor.startswith("https://"):
            return valor
        print("A URL deve iniciar com http:// ou https://")


def main() -> None:
    print("Configurações de acesso do Capacidade Produtiva")

    cp_db_host = _perguntar_texto("Qual endereço de IP do servidor Postgres onde será instalado o banco do CP? ")
    cp_db_port = _perguntar_int("Qual a porta do Postgres do CP? ")
    cp_db_user = _perguntar_texto("Qual o nome do usuário do PostgreSQL para interação com o CP (já deve existir)? ")
    cp_db_password = getpass("Qual a senha deste usuário de interação do CP? ").strip()
    cp_db_name = _perguntar_texto("Qual o nome do banco de dados do Capacidade Produtiva? ")

    cp_api_port = _perguntar_int("Qual porta deseja para o serviço Capacidade Produtiva? ")

    criar_cp = _perguntar_sim_nao("Deseja criar o banco de dados do CP agora")
    if criar_cp:
        usuario_admin = _perguntar_texto("Qual o usuário admin do Postgres para criar banco (ex: postgres)? ")
        senha_admin = getpass("Qual a senha do usuário admin do Postgres? ").strip()
        criado = criar_banco_se_necessario(cp_db_host, cp_db_port, usuario_admin, senha_admin, cp_db_name)
        if criado:
            print(f"Banco '{cp_db_name}' criado com sucesso.")
        else:
            print(f"Banco '{cp_db_name}' já existia, nada a fazer.")

    sap_db_host = _perguntar_texto("Qual endereço de IP do servidor Postgres onde está o SAP a ser espelhado? ")
    sap_db_port = _perguntar_int("Qual a porta do Postgres do SAP? ")
    sap_db_user = _perguntar_texto("Qual o nome do usuário do PostgreSQL que tem acesso ao SAP? ")
    sap_db_password = getpass("Qual a senha do usuário que tem acesso ao SAP? ").strip()
    sap_db_name = _perguntar_texto("Qual o nome do banco do SAP? ")

    auth_url = _perguntar_url_http("Qual a URL do serviço de autenticação (iniciar com http:// ou https://)? ")
    auth_admin_user = _perguntar_texto("Qual o nome do usuário já existente no serviço de autenticação que será admin do CP? ")
    auth_admin_password = getpass("Qual a senha desse usuário admin do Auth? ").strip()

    incluir_sap_test = _perguntar_sim_nao("Você gostaria de incluir as variáveis do SAP_TEST para desenvolvimento")

    sap_test_db_host = ""
    sap_test_db_port = 0
    sap_test_db_name = ""
    sap_test_db_user = ""
    sap_test_db_password = ""

    if incluir_sap_test:
        sap_test_db_host = _perguntar_texto("Qual endereço de IP do servidor Postgres do SAP_TEST? ")
        sap_test_db_port = _perguntar_int("Qual a porta do Postgres do SAP_TEST? ")
        sap_test_db_user = _perguntar_texto("Qual o nome do usuário do PostgreSQL para interação com o SAP_TEST (já deve existir)? ")
        sap_test_db_password = getpass("Qual a senha deste usuário de interação do SAP_TEST? ").strip()
        sap_test_db_name = _perguntar_texto("Qual o nome do banco de dados do SAP_TEST? ")

        criar_sap_test = _perguntar_sim_nao("Deseja criar o banco SAP_TEST agora")
        if criar_sap_test:
            usuario_admin = _perguntar_texto("Qual o usuário admin do Postgres para criar o SAP_TEST (ex: postgres)? ")
            senha_admin = getpass("Qual a senha do usuário admin do Postgres? ").strip()
            criado = criar_banco_se_necessario(sap_test_db_host, sap_test_db_port, usuario_admin, senha_admin, sap_test_db_name)
            if criado:
                print(f"Banco '{sap_test_db_name}' criado com sucesso.")
            else:
                print(f"Banco '{sap_test_db_name}' já existia, nada a fazer.")

    cfg = ConfigEnv(
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
        auth_admin_user=auth_admin_user,
        auth_admin_password=auth_admin_password,
        incluir_sap_test=incluir_sap_test,
        sap_test_db_host=sap_test_db_host,
        sap_test_db_port=sap_test_db_port,
        sap_test_db_name=sap_test_db_name,
        sap_test_db_user=sap_test_db_user,
        sap_test_db_password=sap_test_db_password,
    )

    env_file = Path("config.env")
    escrever_config_env(env_file, cfg)
    print(f"config.env criado com sucesso em {env_file.resolve()}")
