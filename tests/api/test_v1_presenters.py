from gir_api.models import GenerateErrorResponse
from gir_api.presenters import present_generate_v1
from gir_application import (
    GenerateGeometryResult,
    GenerationStatus,
    PipelineFailureStage,
)


def test_presenter_maps_adapter_failure_to_stable_warning() -> None:
    result = GenerateGeometryResult(
        status=GenerationStatus.ERROR,
        confidence=0.0,
        warnings=["No rule matched input."],
        failure_stage=PipelineFailureStage.ADAPTER,
    )

    response = present_generate_v1(result)

    assert isinstance(response, GenerateErrorResponse)
    assert response.warnings[0].code == "unsupported_construction"
    assert response.warnings[0].message == "Construction is not supported."
