from __future__ import annotations

from pathlib import Path

import pytest

from scripts.package_smoke import (
    PUBLIC_PACKAGES,
    find_single_wheel,
    import_smoke_code,
    load_project_metadata,
    venv_cli,
    venv_python,
)


def test_load_project_metadata_reads_current_project() -> None:
    assert load_project_metadata() == ("gir", "0.2.0")


def test_venv_paths_are_cross_platform(tmp_path: Path) -> None:
    venv = tmp_path / "venv"

    assert venv_python(venv, platform_name="posix") == venv / "bin" / "python"
    assert venv_cli(venv, "gir", platform_name="posix") == venv / "bin" / "gir"
    assert venv_python(venv, platform_name="nt") == venv / "Scripts" / "python.exe"
    assert venv_cli(venv, "gir", platform_name="nt") == venv / "Scripts" / "gir.exe"


def test_find_single_wheel_requires_exactly_one_artifact(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="found 0"):
        find_single_wheel(tmp_path)

    first = tmp_path / "gir-0.2.0-py3-none-any.whl"
    first.touch()
    assert find_single_wheel(tmp_path) == first

    (tmp_path / "gir-0.2.1-py3-none-any.whl").touch()
    with pytest.raises(RuntimeError, match="found 2"):
        find_single_wheel(tmp_path)


def test_import_smoke_code_covers_all_public_packages() -> None:
    code = import_smoke_code("gir", "0.2.0")

    for package in PUBLIC_PACKAGES:
        assert package in code
    assert "version('gir')" in code
    assert "'0.2.0'" in code
