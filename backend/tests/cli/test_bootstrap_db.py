# caminho: backend/tests/cli/test_bootstrap_db.py

from __future__ import annotations

import pytest

from cp.cli import bootstrap_db


def test_validar_nome_banco_aceita_nome_simples() -> None:
    bootstrap_db._validar_nome_banco("cp_2026")


@pytest.mark.parametrize(
    "nome_invalido",
    [
        "cp-prod",
        "cp prod",
        "cp;DROP DATABASE postgres;",
        'cp"xx',
        "cp/xx",
        "",
        "   ",
    ],
)
def test_validar_nome_banco_rejeita_caracteres_invalidos(nome_invalido: str) -> None:
    with pytest.raises(ValueError):
        bootstrap_db._validar_nome_banco(nome_invalido)


def test_criar_banco_retorna_false_quando_ja_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    def database_existe(_engine: object, _db: str) -> bool:
        return True

    chamadas: dict[str, int] = {"criou": 0}

    def criar_database(_engine: object, _db: str) -> None:
        chamadas["criou"] += 1

    def create_engine_fake(_dsn: str, future: bool = True) -> object:
        return object()

    monkeypatch.setattr(bootstrap_db, "_database_exists", database_existe)
    monkeypatch.setattr(bootstrap_db, "_create_database", criar_database)
    monkeypatch.setattr(bootstrap_db, "create_engine", create_engine_fake)

    criado = bootstrap_db.criar_banco(
        host="localhost",
        port=5432,
        usuario_admin="postgres",
        senha_admin="postgres",
        nome_banco="capacidade_produtiva",
    )

    assert criado is False
    assert chamadas["criou"] == 0


def test_criar_banco_retorna_true_quando_cria(monkeypatch: pytest.MonkeyPatch) -> None:
    def database_existe(_engine: object, _db: str) -> bool:
        return False

    chamadas: dict[str, int] = {"criou": 0}

    def criar_database(_engine: object, _db: str) -> None:
        chamadas["criou"] += 1

    def create_engine_fake(_dsn: str, future: bool = True) -> object:
        return object()

    monkeypatch.setattr(bootstrap_db, "_database_exists", database_existe)
    monkeypatch.setattr(bootstrap_db, "_create_database", criar_database)
    monkeypatch.setattr(bootstrap_db, "create_engine", create_engine_fake)

    criado = bootstrap_db.criar_banco(
        host="localhost",
        port=5432,
        usuario_admin="postgres",
        senha_admin="postgres",
        nome_banco="capacidade_produtiva",
    )

    assert criado is True
    assert chamadas["criou"] == 1


def test_criar_banco_cp_cria_schemas_mesmo_se_banco_ja_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    def criar_banco_fake(**_kwargs: object) -> bool:
        return False

    chamadas: dict[str, int] = {"schemas": 0, "views": 0, "kpi": 0}

    def criar_schemas_fake(_engine_cp: object) -> None:
        chamadas["schemas"] += 1

    def garantir_views_fake(_engine_cp: object) -> None:
        chamadas["views"] += 1

    def garantir_kpi_fake(_engine_cp: object) -> None:
        chamadas["kpi"] += 1

    def create_engine_fake(_dsn: str, future: bool = True) -> object:
        return object()

    monkeypatch.setattr(bootstrap_db, "criar_banco", criar_banco_fake)
    monkeypatch.setattr(bootstrap_db, "_criar_schemas_cp", criar_schemas_fake)
    monkeypatch.setattr(bootstrap_db, "garantir_views_analytics", garantir_views_fake)
    monkeypatch.setattr(bootstrap_db, "garantir_tabelas_kpi", garantir_kpi_fake)
    monkeypatch.setattr(bootstrap_db, "create_engine", create_engine_fake)

    criado_agora = bootstrap_db.criar_banco_cp(
        host="localhost",
        port=5432,
        usuario_admin="postgres",
        senha_admin="postgres",
        nome_banco="capacidade_produtiva",
    )

    assert criado_agora is False
    assert chamadas["schemas"] == 1
    assert chamadas["views"] == 1
    assert chamadas["kpi"] == 1


def test_criar_banco_cp_retorna_true_quando_criou_banco_e_garante_schemas(monkeypatch: pytest.MonkeyPatch) -> None:
    def criar_banco_fake(**_kwargs: object) -> bool:
        return True

    chamadas: dict[str, int] = {"schemas": 0, "views": 0, "kpi": 0}

    def criar_schemas_fake(_engine_cp: object) -> None:
        chamadas["schemas"] += 1

    def garantir_views_fake(_engine_cp: object) -> None:
        chamadas["views"] += 1

    def garantir_kpi_fake(_engine_cp: object) -> None:
        chamadas["kpi"] += 1

    def create_engine_fake(_dsn: str, future: bool = True) -> object:
        return object()

    monkeypatch.setattr(bootstrap_db, "criar_banco", criar_banco_fake)
    monkeypatch.setattr(bootstrap_db, "_criar_schemas_cp", criar_schemas_fake)
    monkeypatch.setattr(bootstrap_db, "garantir_views_analytics", garantir_views_fake)
    monkeypatch.setattr(bootstrap_db, "garantir_tabelas_kpi", garantir_kpi_fake)
    monkeypatch.setattr(bootstrap_db, "create_engine", create_engine_fake)

    criado_agora = bootstrap_db.criar_banco_cp(
        host="localhost",
        port=5432,
        usuario_admin="postgres",
        senha_admin="postgres",
        nome_banco="capacidade_produtiva",
    )

    assert criado_agora is True
    assert chamadas["schemas"] == 1
    assert chamadas["views"] == 1
    assert chamadas["kpi"] == 1


def test_schemas_cp_contem_agregacao_e_dominio() -> None:
    assert "agregacao" in bootstrap_db._SCHEMAS_CP
    assert "dominio" in bootstrap_db._SCHEMAS_CP
