import json
from pathlib import Path
from typing import Any

from gir_benchmarks.runner import run_benchmarks
from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene
from gir_render.svg_renderer import render_svg
from gir_render.tikz_renderer import render_tikz

ROOT = Path(__file__).resolve().parents[1]
SVG_BENCHMARKS = ROOT / "benchmarks" / "gir_to_svg"
TIKZ_BENCHMARKS = ROOT / "benchmarks" / "gir_to_tikz"


def _expected_file(path: Path) -> Path:
    return path.with_name(path.name.replace(".gir.json", ".expected.json"))


def _assert_render_scenes_are_valid(directory: Path) -> None:
    for path in directory.glob("*.gir.json"):
        scene = GirScene.model_validate_json(path.read_text(encoding="utf-8"))
        report = validate_scene(scene)
        assert report.is_valid, f"{path}: {report.issues}"


def _assert_expected_files_exist(directory: Path) -> None:
    for path in directory.glob("*.gir.json"):
        assert _expected_file(path).exists(), f"Missing expected file for {path}"


def _assert_expected_shape(directory: Path, expected_type: str) -> None:
    for path in directory.glob("*.expected.json"):
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        assert data["type"] == expected_type
        assert isinstance(data["must_contain"], list)
        assert isinstance(data["must_not_contain"], list)
        assert isinstance(data["min_occurrences"], dict)


def test_gir_to_svg_benchmark_scenes_are_valid() -> None:
    _assert_render_scenes_are_valid(SVG_BENCHMARKS)


def test_gir_to_tikz_benchmark_scenes_are_valid() -> None:
    _assert_render_scenes_are_valid(TIKZ_BENCHMARKS)


def test_render_benchmark_expected_files_exist() -> None:
    _assert_expected_files_exist(SVG_BENCHMARKS)
    _assert_expected_files_exist(TIKZ_BENCHMARKS)


def test_render_benchmark_expected_files_have_supported_shape() -> None:
    _assert_expected_shape(SVG_BENCHMARKS, "svg")
    _assert_expected_shape(TIKZ_BENCHMARKS, "tikz")


def test_benchmark_runner_includes_render_suites() -> None:
    summary = run_benchmarks(root=ROOT)

    assert summary["failed"] == 0
    assert summary["suites"]["gir_to_svg"]["total"] >= 3
    assert summary["suites"]["gir_to_tikz"]["total"] >= 3


def test_render_svg_triangle_benchmark_output_contains_contract_markers() -> None:
    scene = GirScene.model_validate_json(
        (SVG_BENCHMARKS / "triangle_001.gir.json").read_text(encoding="utf-8")
    )

    output = render_svg(scene)

    assert "<svg" in output
    assert "A" in output
    assert "B" in output
    assert "C" in output


def test_render_tikz_triangle_benchmark_output_contains_contract_markers() -> None:
    scene = GirScene.model_validate_json(
        (TIKZ_BENCHMARKS / "triangle_001.gir.json").read_text(encoding="utf-8")
    )

    output = render_tikz(scene)

    assert "\\begin{tikzpicture}" in output
    assert "\\draw" in output
    assert "A" in output
    assert "B" in output
    assert "C" in output


def test_render_benchmark_inputs_are_canonical_gir_0_2() -> None:
    for directory in (SVG_BENCHMARKS, TIKZ_BENCHMARKS):
        for path in directory.glob("*.gir.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload["schema_version"] == "0.2.0", path
            assert "version" not in payload, path
