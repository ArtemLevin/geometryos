import json
from pathlib import Path
from typing import Any

from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


def gir_json_schema() -> dict[str, Any]:
    """Return the canonical machine-readable JSON Schema for GIR scenes."""
    return GirScene.model_json_schema()


def validation_report_json_schema() -> dict[str, Any]:
    """Return the JSON Schema for public validation report payloads."""
    return ValidationReport.model_json_schema()


def write_gir_schema(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_schema_json(gir_json_schema()) + "\n", encoding="utf-8")
    return output


def check_gir_schema(output: Path) -> bool:
    if not output.exists():
        return False
    committed = json.loads(output.read_text(encoding="utf-8"))
    return _schema_json(committed) == _schema_json(gir_json_schema())


def _schema_json(schema: dict[str, Any]) -> str:
    # Design note: sorted keys make schema-check deterministic and keep the committed
    # machine contract reviewable even though Pydantic emits a large schema artifact.
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)
