# caminho: backend/tests/cli/test_db.py
"""Testes das funções de banco de dados do CLI."""

from __future__ import annotations

import pytest

from cp.cli import db


def test_validar_nome_banco_aceita_nome_simples() -> None:
    db._validar_nome_banco("cp_2026")


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
        db._validar_nome_banco(nome_invalido)


def test_criar_banco_retorna_false_quando_ja_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    def database_existe(_engine: object, _db: str) -> bool:
        return True

    chamadas: dict[str, int] = {"criou": 0}

    def criar_database(_engine: object, _db: str) -> None:
        chamadas["criou"] += 1

    def create_engine_fake(_dsn: str, future: bool = True) -> object:
        return object()

    monkeypatch.setattr(db, "_database_exists", database_existe)
    monkeypatch.setattr(db, "_create_database", criar_database)
    monkeypatch.setattr(db, "create_engine", create_engine_fake)

    criado = db.criar_banco(
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

    monkeypatch.setattr(db, "_database_exists", database_existe)
    monkeypatch.setattr(db, "_create_database", criar_database)
    monkeypatch.setattr(db, "create_engine", create_engine_fake)

    criado = db.criar_banco(
        host="localhost",
        port=5432,
        usuario_admin="postgres",
        senha_admin="postgres",
        nome_banco="capacidade_produtiva",
    )

    assert criado is True
    assert chamadas["criou"] == 1


def test_criar_banco_cp_cria_schemas_e_kpi_mesmo_se_banco_ja_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quando o banco já existe, ainda assim garante schemas e tabelas KPI."""

    def criar_banco_fake(**_kwargs: object) -> bool:
        return False  # Banco já existia

    chamadas: dict[str, int] = {"schemas": 0, "kpi": 0}

    def criar_schemas_fake(_engine_cp: object) -> None:
        chamadas["schemas"] += 1

    def garantir_kpi_fake(_engine_cp: object) -> None:
        chamadas["kpi"] += 1

    def create_engine_fake(_dsn: str, future: bool = True) -> object:
        return object()

    monkeypatch.setattr(db, "criar_banco", criar_banco_fake)
    monkeypatch.setattr(db, "_criar_schemas_cp", criar_schemas_fake)
    monkeypatch.setattr(db, "garantir_tabelas_kpi", garantir_kpi_fake)
    monkeypatch.setattr(db, "create_engine", create_engine_fake)

    criado_agora = db.criar_banco_cp(
        host="localhost",
        port=5432,
        usuario_admin="postgres",
        senha_admin="postgres",
        nome_banco="capacidade_produtiva",
    )

    assert criado_agora is False
    assert chamadas["schemas"] == 1
    assert chamadas["kpi"] == 1


def test_criar_banco_cp_retorna_true_quando_criou_banco_e_garante_schemas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quando o banco é criado, retorna True e garante schemas e tabelas KPI."""

    def criar_banco_fake(**_kwargs: object) -> bool:
        return True  # Banco criado agora

    chamadas: dict[str, int] = {"schemas": 0, "kpi": 0}

    def criar_schemas_fake(_engine_cp: object) -> None:
        chamadas["schemas"] += 1

    def garantir_kpi_fake(_engine_cp: object) -> None:
        chamadas["kpi"] += 1

    def create_engine_fake(_dsn: str, future: bool = True) -> object:
        return object()

    monkeypatch.setattr(db, "criar_banco", criar_banco_fake)
    monkeypatch.setattr(db, "_criar_schemas_cp", criar_schemas_fake)
    monkeypatch.setattr(db, "garantir_tabelas_kpi", garantir_kpi_fake)
    monkeypatch.setattr(db, "create_engine", create_engine_fake)

    criado_agora = db.criar_banco_cp(
        host="localhost",
        port=5432,
        usuario_admin="postgres",
        senha_admin="postgres",
        nome_banco="capacidade_produtiva",
    )

    assert criado_agora is True
    assert chamadas["schemas"] == 1
    assert chamadas["kpi"] == 1


def test_schemas_cp_contem_agregacao_e_dominio() -> None:
    assert "agregacao" in db._SCHEMAS_CP
    assert "dominio" in db._SCHEMAS_CP
