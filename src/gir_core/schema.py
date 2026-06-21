from typing import Any

from gir_core.models.scene import GirScene


def gir_json_schema() -> dict[str, Any]:
    return GirScene.model_json_schema()
