from pathlib import Path

from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_files_exist() -> None:
    assert (ROOT / "benchmarks/text_to_gir/altitude/altitude_001.input.txt").exists()
    assert (ROOT / "benchmarks/text_to_gir/median/median_001.expected.gir.json").exists()
    assert (ROOT / "benchmarks/text_to_gir/ambiguous/ambiguous_bisector_001.expected.json").exists()


def test_expected_gir_files_parse_and_validate() -> None:
    for path in (ROOT / "benchmarks/text_to_gir").glob("*/*.expected.gir.json"):
        scene = GirScene.model_validate_json(path.read_text())
        assert validate_scene(scene).is_valid, path
