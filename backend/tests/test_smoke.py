# Testes de smoke: verificam que o pacote está instalado corretamente
# e que a aplicação FastAPI é instanciável.
#
# "Smoke test" é o teste mais básico possível — se isso falhar,
# nem adianta rodar os testes de negócio. Nome vem da eletrônica:
# você liga o circuito e verifica se tem fumaça antes de testar funcionalidades.

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cp import __version__
from cp.main import app


def test_package_version_is_defined() -> None:
    """O pacote deve ter uma versão semântica definida."""
    assert __version__ == "0.1.0"


def test_version_format_is_semver() -> None:
    """A versão deve seguir o formato MAJOR.MINOR.PATCH."""
    parts = __version__.split(".")
    assert len(parts) == 3, f"Versão '{__version__}' não está no formato semver"
    assert all(part.isdigit() for part in parts), "Todas as partes devem ser numéricas"


def test_app_is_fastapi_instance() -> None:
    """O módulo cp.main deve exportar uma instância FastAPI como 'app'."""
    assert isinstance(app, FastAPI)


def test_health_endpoint_returns_ok() -> None:
    """GET /api/health deve retornar 200 com status ok."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
