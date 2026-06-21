import json
from pathlib import Path

from gir_core.models.scene import GirScene

ROOT = Path(__file__).resolve().parents[1]


def export_schema() -> Path:
    output = ROOT / "schemas" / "gir.schema.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(GirScene.model_json_schema(), ensure_ascii=False, indent=2) + "
")
    return output


if __name__ == "__main__":
    path = export_schema()
    print(f"Exported GIR schema to {path}")
