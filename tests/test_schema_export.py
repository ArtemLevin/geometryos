import json
from pathlib import Path

from gir_core.models.scene import GirScene
from gir_core.schema import gir_json_schema
from scripts.export_schema import export_schema, schema_is_up_to_date


def test_schema_export_generates_file() -> None:
    path = export_schema()
    assert path.exists()
    schema = json.loads(Path(path).read_text(encoding="utf-8"))
    assert schema["title"] == "GirScene"


def test_schema_contains_object_definitions() -> None:
    schema = gir_json_schema()
    assert "$defs" in schema
    assert "PointObject" in schema["$defs"]
    assert "TriangleObject" in schema["$defs"]


def test_schema_contains_constraint_definitions() -> None:
    schema = gir_json_schema()
    assert "$defs" in schema
    assert "AltitudeConstraint" in schema["$defs"]
    assert "MedianConstraint" in schema["$defs"]
    assert "PerpendicularConstraint" in schema["$defs"]


def test_committed_schema_is_up_to_date() -> None:
    generated = GirScene.model_json_schema()
    committed = json.loads(Path("schemas/gir.schema.json").read_text(encoding="utf-8"))
    assert json.dumps(committed, sort_keys=True) == json.dumps(generated, sort_keys=True)
    assert schema_is_up_to_date()
