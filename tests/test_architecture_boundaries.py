from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _assert_no_forbidden_imports(path: Path, forbidden: tuple[str, ...]) -> None:
    violations = sorted(
        module
        for module in _imports(path)
        if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)
    )
    assert not violations, f"{path.relative_to(ROOT)} imports forbidden modules: {violations}"


def test_api_routes_do_not_orchestrate_geometry_implementations() -> None:
    forbidden = (
        "gir_ai.text_to_gir.adapter",
        "gir_core.normalize",
        "gir_core.validation.semantic_validator",
        "gir_render.svg_renderer",
        "gir_render.tikz_renderer",
    )
    for path in (ROOT / "src/gir_api/routes").glob("*.py"):
        _assert_no_forbidden_imports(path, forbidden)


def test_cli_does_not_orchestrate_geometry_implementations() -> None:
    _assert_no_forbidden_imports(
        ROOT / "src/gir_cli/main.py",
        (
            "gir_core.normalize",
            "gir_core.validation.semantic_validator",
            "gir_render.svg_renderer",
            "gir_render.tikz_renderer",
        ),
    )


def test_application_layer_is_transport_agnostic() -> None:
    for path in (ROOT / "src/gir_application").glob("*.py"):
        _assert_no_forbidden_imports(path, ("fastapi", "typer", "gir_api", "gir_cli"))


def test_core_does_not_depend_on_outer_layers() -> None:
    for path in (ROOT / "src/gir_core").rglob("*.py"):
        _assert_no_forbidden_imports(
            path,
            ("gir_application", "gir_api", "gir_cli", "gir_ai", "gir_render"),
        )
