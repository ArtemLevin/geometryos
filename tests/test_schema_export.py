import json
from pathlib import Path

from scripts.export_schema import export_schema


def test_schema_export_generates_file() -> None:
    path = export_schema()
    assert path.exists()
    schema = json.loads(Path(path).read_text())
    assert schema["title"] == "GirScene"
