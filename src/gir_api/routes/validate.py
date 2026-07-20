from fastapi import APIRouter

from gir_application import validate_geometry
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationReport

router = APIRouter()


@router.post("/validate-gir")
def validate_gir(scene: GirScene) -> ValidationReport:
    return validate_geometry(scene)
