from fastapi import APIRouter

from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport
from gir_core.validation.semantic_validator import validate_scene

router = APIRouter()


@router.post("/validate-gir")
def validate_gir(scene: GirScene) -> ValidationReport:
    return validate_scene(scene)
