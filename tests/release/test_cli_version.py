from typer.testing import CliRunner

from gir_cli.main import app

runner = CliRunner()


def test_cli_reports_geometryos_release_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "GeometryOS 0.2.0"


def test_cli_help_preserves_existing_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("validate", "render-svg", "render-tikz", "benchmark", "export-schema"):
        assert command in result.stdout
