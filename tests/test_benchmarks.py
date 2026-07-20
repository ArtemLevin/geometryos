import json
from pathlib import Path

from gir_ai.text_to_gir.adapter import text_to_gir
from gir_benchmarks.runner import _compare_result, run_benchmarks
from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene
from scripts.run_benchmarks import main as run_benchmarks_script

ROOT = Path(__file__).resolve().parents[1]
TEXT_TO_GIR = ROOT / "benchmarks" / "text_to_gir"


def test_benchmark_files_exist() -> None:
    assert (TEXT_TO_GIR / "triangle/triangle_001.input.txt").exists()
    assert (TEXT_TO_GIR / "altitude/altitude_001.input.txt").exists()
    assert (TEXT_TO_GIR / "median/median_001.expected.gir.json").exists()
    assert (TEXT_TO_GIR / "ambiguous/ambiguous_bisector_001.expected.json").exists()
    assert (TEXT_TO_GIR / "unsupported/unsupported_square_001.expected.json").exists()


def test_expected_gir_files_parse_and_validate() -> None:
    for path in TEXT_TO_GIR.glob("*/*.expected.gir.json"):
        scene = GirScene.model_validate_json(path.read_text(encoding="utf-8"))
        report = validate_scene(scene)
        assert report.is_valid, f"{path}: {report.issues}"


def test_non_gir_expected_files_have_supported_status() -> None:
    for path in TEXT_TO_GIR.glob("*/*.expected.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["status"] in {"success", "needs_clarification", "error"}


def test_benchmark_runner_returns_summary() -> None:
    summary = run_benchmarks(root=ROOT)
    assert summary["total"] >= 10
    assert summary["failed"] == 0
    assert summary["passed"] == summary["total"]
    assert summary["failures"] == []


def test_script_wrapper_uses_shared_runner_summary() -> None:
    assert run_benchmarks_script() == 0


def test_soft_comparison_detects_missing_expected_object_id() -> None:
    result = text_to_gir("Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.")
    assert result.gir is not None
    expected = result.gir.model_dump()
    expected["objects"].append({"id": "ZZ", "type": "point", "label": "ZZ"})

    errors = _compare_result(result, expected)

    assert any("missing expected object ids: ZZ" in error for error in errors)


def test_soft_comparison_detects_missing_ambiguity_code() -> None:
    result = text_to_gir("Постройте треугольник ABC. Проведите биссектрису.")

    errors = _compare_result(
        result,
        {"status": "needs_clarification", "ambiguities": [{"code": "other_code"}]},
    )

    assert errors == ["missing expected ambiguity codes: other_code"]


def test_text_to_gir_success_fixtures_are_canonical_gir_0_2() -> None:
    for path in TEXT_TO_GIR.glob("*/*.expected.gir.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "0.2.0", path
        assert "version" not in payload, path
