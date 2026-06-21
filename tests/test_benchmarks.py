from pathlib import Path

from gir_ai.text_to_gir.adapter import text_to_gir
from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene
from scripts.run_benchmarks import _compare_result, run_benchmarks

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_files_exist() -> None:
    assert (ROOT / "benchmarks/text_to_gir/altitude/altitude_001.input.txt").exists()
    assert (ROOT / "benchmarks/text_to_gir/median/median_001.expected.gir.json").exists()
    assert (ROOT / "benchmarks/text_to_gir/ambiguous/ambiguous_bisector_001.expected.json").exists()


def test_expected_gir_files_parse_and_validate() -> None:
    for path in (ROOT / "benchmarks/text_to_gir").glob("*/*.expected.gir.json"):
        scene = GirScene.model_validate_json(path.read_text())
        assert validate_scene(scene).is_valid, path


def test_run_benchmarks_soft_comparison_passes_current_fixtures() -> None:
    summary = run_benchmarks()
    assert summary["failed"] == 0
    assert summary["passed"] == summary["total"]


def test_soft_comparison_detects_missing_expected_object_id() -> None:
    result = text_to_gir(
        "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."
    )
    assert result.gir is not None
    expected = result.gir.model_dump()
    expected["objects"].append({"id": "ZZ", "type": "point", "label": "ZZ"})

    errors = _compare_result(result, expected)

    assert any("missing expected object ids: ZZ" in error for error in errors)
