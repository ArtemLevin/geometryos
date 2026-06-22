from typing import Any

from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport


def gir_json_schema() -> dict[str, Any]:
    """Return the canonical machine-readable JSON Schema for GIR scenes."""
    return GirScene.model_json_schema()


def validation_report_json_schema() -> dict[str, Any]:
    """Return the JSON Schema for public validation report payloads."""
    return ValidationReport.model_json_schema()
