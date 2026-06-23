from scripts.verify import CHECKS


def test_verify_includes_required_checks() -> None:
    names = {check.name for check in CHECKS}

    assert "ruff" in names
    assert "format" in names
    assert "mypy" in names
    assert "pytest" in names
    assert "schema" in names
    assert "benchmarks" in names
    assert "cli benchmark" in names
    assert "cli schema check" in names


def test_verify_cli_smoke_uses_explicit_paths() -> None:
    commands = {check.name: check.command for check in CHECKS}

    assert commands["cli benchmark"] == ["uv", "run", "gir", "benchmark", "--root", "."]
    assert commands["cli schema check"] == [
        "uv",
        "run",
        "gir",
        "export-schema",
        "--check",
        "--output",
        "schemas/gir.schema.json",
    ]
