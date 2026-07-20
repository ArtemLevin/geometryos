from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

from scripts import verify
from scripts.verify import CHECKS, Check

EXPECTED_CHECK_NAMES = [
    "ruff",
    "format",
    "mypy",
    "pytest",
    "schema",
    "benchmarks",
    "cli benchmark",
    "cli schema check",
]


def test_verify_includes_required_checks_in_stable_order() -> None:
    assert [check.name for check in CHECKS] == EXPECTED_CHECK_NAMES
    assert len({check.name for check in CHECKS}) == len(CHECKS)


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


def test_run_check_uses_repository_root(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> CompletedProcess[str]:
        captured.update(command=command, cwd=cwd, check=check)
        return CompletedProcess(command, 0)

    monkeypatch.setattr(verify.subprocess, "run", fake_run)
    monkeypatch.setattr(verify, "monotonic", iter([10.0, 10.25]).__next__)

    result = verify.run_check(Check("sample", ["python", "-V"]))

    assert result == 0
    assert captured == {
        "command": ["python", "-V"],
        "cwd": verify.ROOT,
        "check": False,
    }
    assert "[PASS] sample (0.25s)" in capsys.readouterr().out


def test_main_stops_after_first_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    results: Iterator[int] = iter([0, 7])
    visited: list[str] = []

    def fake_run_check(check: Check) -> int:
        visited.append(check.name)
        return next(results)

    monkeypatch.setattr(verify, "CHECKS", [Check("first", []), Check("second", []), Check("third", [])])
    monkeypatch.setattr(verify, "run_check", fake_run_check)

    assert verify.main() == 7
    assert visited == ["first", "second"]


def test_main_reports_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(verify, "CHECKS", [Check("first", []), Check("second", [])])
    monkeypatch.setattr(verify, "run_check", lambda check: 0)

    assert verify.main() == 0
    assert "All verification checks passed." in capsys.readouterr().out
