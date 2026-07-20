import json
from pathlib import Path

from typer.testing import CliRunner

from gir_cli.main import app

ROOT = Path(__file__).resolve().parents[1]
VALID_SCENE = ROOT / "benchmarks" / "text_to_gir" / "altitude" / "altitude_001.expected.gir.json"


def test_cli_benchmark_with_root() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["benchmark", "--root", str(ROOT)])

    assert result.exit_code == 0
    assert '"failed": 0' in result.output


def test_cli_validate_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["validate", str(VALID_SCENE)])

    assert result.exit_code == 0
    assert '"is_valid": true' in result.output


def test_cli_render_svg_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["render-svg", str(VALID_SCENE)])

    assert result.exit_code == 0
    assert "<svg" in result.output


def test_cli_render_tikz_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["render-tikz", str(VALID_SCENE)])

    assert result.exit_code == 0
    assert "\\begin{tikzpicture}" in result.output


def test_cli_benchmark_with_benchmarks_dir() -> None:
    runner = CliRunner()
    benchmarks_dir = ROOT / "benchmarks" / "text_to_gir"

    result = runner.invoke(app, ["benchmark", "--benchmarks-dir", str(benchmarks_dir)])

    assert result.exit_code == 0
    assert '"failed": 0' in result.output


def test_cli_benchmark_missing_dir_exits_1(tmp_path: Path) -> None:
    runner = CliRunner()
    missing = tmp_path / "missing"

    result = runner.invoke(app, ["benchmark", "--benchmarks-dir", str(missing)])

    assert result.exit_code == 1
    assert "Benchmarks directory not found" in result.output


def test_cli_export_schema_writes_output(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "gir.schema.json"

    result = runner.invoke(app, ["export-schema", "--output", str(output)])

    assert result.exit_code == 0
    assert output.exists()
    assert '"$defs"' in output.read_text(encoding="utf-8")


def test_cli_export_schema_check_passes_for_fresh_schema(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "gir.schema.json"

    write_result = runner.invoke(app, ["export-schema", "--output", str(output)])
    assert write_result.exit_code == 0

    check_result = runner.invoke(app, ["export-schema", "--check", "--output", str(output)])

    assert check_result.exit_code == 0
    assert "up to date" in check_result.output.lower()


def test_cli_export_schema_check_fails_for_stale_schema(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "gir.schema.json"
    output.write_text('{"stale": true}\n', encoding="utf-8")

    result = runner.invoke(app, ["export-schema", "--check", "--output", str(output)])

    assert result.exit_code == 1
    assert "out of date" in result.output.lower()


def test_cli_validate_accepts_legacy_gir_0_1() -> None:
    runner = CliRunner()
    legacy = ROOT / "tests/fixtures/gir/v0_1/altitude.legacy.gir.json"
    result = runner.invoke(app, ["validate", str(legacy)])

    assert result.exit_code == 0
    assert '"is_valid": true' in result.output


def test_cli_validate_rejects_unknown_schema_version(tmp_path: Path) -> None:
    runner = CliRunner()
    payload = json.loads(VALID_SCENE.read_text(encoding="utf-8"))
    payload["schema_version"] = "0.3.0"
    future_scene = tmp_path / "future.gir.json"
    future_scene.write_text(json.dumps(payload), encoding="utf-8")

    result = runner.invoke(app, ["validate", str(future_scene)])

    assert result.exit_code != 0
