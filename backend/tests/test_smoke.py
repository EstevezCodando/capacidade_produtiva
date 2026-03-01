# Testes de smoke: verificam que o pacote está instalado corretamente
# e que o ponto de entrada é executável.
#
# "Smoke test" é o teste mais básico possível — se isso falhar,
# nem adianta rodar os testes de negócio. Nome vem da eletrônica:
# você liga o circuito e verifica se tem fumaça antes de testar funcionalidades.


from cp import __version__
from cp.main import main


def test_package_version_is_defined() -> None:
    """O pacote deve ter uma versão semântica definida."""
    assert __version__ == "0.1.0"


def test_version_format_is_semver() -> None:
    """A versão deve seguir o formato MAJOR.MINOR.PATCH."""
    parts = __version__.split(".")
    assert len(parts) == 3, f"Versão '{__version__}' não está no formato semver"
    assert all(part.isdigit() for part in parts), "Todas as partes devem ser numéricas"


def test_main_executes_without_error(capsys: object) -> None:
    """O ponto de entrada deve executar sem lançar exceção."""
    # Se main() lançar qualquer exceção, o teste falha automaticamente.
    # Isso garante que o entrypoint do Docker funciona.
    main()
