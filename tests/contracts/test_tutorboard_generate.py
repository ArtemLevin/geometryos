from typing import Any

from gir_api.models import (
    GenerateClarificationResponse,
    GenerateErrorResponse,
    GenerateSuccessResponse,
)


def test_tutorboard_generate_fixtures_execute(client: Any, contract_json: Any) -> None:
    cases = [
        ("generate-success", GenerateSuccessResponse),
        ("generate-ambiguity", GenerateClarificationResponse),
        ("generate-unsupported", GenerateErrorResponse),
    ]
    for name, model in cases:
        response = client.post(
            "/api/v1/generate",
            json=contract_json(f"{name}.request.json"),
            headers={"X-Request-ID": "tutorboard-contract"},
        )
        assert response.status_code == 200
        assert response.json() == contract_json(f"{name}.response.json")
        model.model_validate(response.json())
        assert response.headers["X-Request-ID"] == "tutorboard-contract"
