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
        "anyio",
        "pydantic_settings",
    )
    for path in (ROOT / "src/gir_api/routes").glob("*.py"):
        _assert_no_forbidden_imports(path, forbidden)


def test_api_contract_models_and_presenters_are_transport_agnostic() -> None:
    for filename in ("models.py", "presenters.py"):
        _assert_no_forbidden_imports(
            ROOT / "src/gir_api" / filename,
            ("fastapi", "starlette"),
        )


def test_cli_does_not_orchestrate_geometry_implementations() -> None:
    _assert_no_forbidden_imports(
        ROOT / "src/gir_cli/main.py",
        (
            "gir_core.normalize",
            "gir_core.validation.semantic_validator",
            "gir_render.svg_renderer",
            "gir_render.tikz_renderer",
            "gir_api.readiness",
            "uvicorn",
        ),
    )


def test_application_layer_is_transport_agnostic() -> None:
    for path in (ROOT / "src/gir_application").glob("*.py"):
        _assert_no_forbidden_imports(
            path,
            (
                "fastapi",
                "typer",
                "gir_api",
                "gir_cli",
                "gir_meta",
                "anyio",
                "pydantic_settings",
                "uvicorn",
                "signal",
                "contracts",
            ),
        )


def test_core_does_not_depend_on_outer_layers() -> None:
    for path in (ROOT / "src/gir_core").rglob("*.py"):
        _assert_no_forbidden_imports(
            path,
            (
                "gir_application",
                "gir_api",
                "gir_cli",
                "gir_ai",
                "gir_render",
                "gir_meta",
                "anyio",
                "pydantic_settings",
                "uvicorn",
                "signal",
                "contracts",
            ),
        )


def test_release_metadata_package_is_a_standard_library_leaf() -> None:
    for path in (ROOT / "src/gir_meta").rglob("*.py"):
        _assert_no_forbidden_imports(
            path,
            (
                "gir_core",
                "gir_application",
                "gir_ai",
                "gir_render",
                "gir_api",
                "gir_cli",
                "fastapi",
                "pydantic",
                "typer",
            ),
        )


def test_api_runtime_boundaries_do_not_import_geometry_implementations() -> None:
    forbidden = (
        "gir_ai",
        "gir_core.normalize",
        "gir_core.validation.semantic_validator",
        "gir_render",
    )
    for filename in (
        "context.py",
        "errors.py",
        "exception_handlers.py",
        "logging.py",
        "middleware.py",
        "openapi_contract.py",
        "openapi_examples.py",
        "openapi_compatibility.py",
        "problem_details.py",
        "readiness.py",
        "settings.py",
    ):
        _assert_no_forbidden_imports(ROOT / "src/gir_api" / filename, forbidden)


def test_readiness_probe_does_not_execute_geometry_or_network_work() -> None:
    _assert_no_forbidden_imports(
        ROOT / "src/gir_api/readiness.py",
        (
            "anyio",
            "urllib",
            "httpx",
            "gir_application",
            "gir_ai",
            "gir_render",
            "gir_core.normalize",
            "gir_core.validation.semantic_validator",
        ),
    )


def test_openapi_contract_does_not_import_contract_fixtures() -> None:
    for filename in ("openapi_contract.py", "openapi_examples.py"):
        _assert_no_forbidden_imports(
            ROOT / "src/gir_api" / filename,
            ("contracts", "scripts.export_openapi", "scripts.export_tutorboard_contracts"),
        )
