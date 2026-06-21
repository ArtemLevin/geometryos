import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gir_ai.text_to_gir.adapter import text_to_gir  # noqa: E402
from gir_core.models.scene import GirScene  # noqa: E402
from gir_core.validation.semantic_validator import validate_scene  # noqa: E402


def run_benchmarks() -> dict[str, Any]:
    total = passed = failed = 0
    failures: list[str] = []
    for input_file in sorted((ROOT / "benchmarks" / "text_to_gir").glob("*/*.input.txt")):
        total += 1
        result = text_to_gir(input_file.read_text(encoding="utf-8"))
        expected_file = _expected_file(input_file)
        expected = json.loads(expected_file.read_text(encoding="utf-8"))
        expected_status = expected.get("status", "success")
        ok = result.status == expected_status
        if ok and result.status == "success":
            ok = result.gir is not None and validate_scene(result.gir).is_valid
            if ok and result.gir is not None:
                GirScene.model_validate(result.gir.model_dump())
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append(str(input_file.relative_to(ROOT)))
    summary = {"total": total, "passed": passed, "failed": failed, "failures": failures}
    print(f"total={total} passed={passed} failed={failed}")
    return summary


def _expected_file(input_file: Path) -> Path:
    gir = input_file.with_name(input_file.name.replace(".input.txt", ".expected.gir.json"))
    if gir.exists():
        return gir
    return input_file.with_name(input_file.name.replace(".input.txt", ".expected.json"))


if __name__ == "__main__":
    raise SystemExit(0 if run_benchmarks()["failed"] == 0 else 1)
