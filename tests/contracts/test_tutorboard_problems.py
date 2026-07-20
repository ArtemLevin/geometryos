import time
from typing import Any

from fastapi.testclient import TestClient

from gir_api.execution import TimedApplicationExecutor
from gir_api.main import create_app
from gir_api.problem_details import ProblemDetail
from gir_api.settings import ApiSettings
from gir_application import GenerateGeometryCommand, generate_geometry


def test_request_validation_problem_fixture(client: Any, contract_json: Any) -> None:
    response = client.post(
        "/api/v1/generate",
        json=contract_json("generate-invalid.request.json"),
        headers={"X-Request-ID": "tutorboard-contract"},
    )
    assert response.status_code == 422
    assert response.json() == contract_json("request-validation.problem.json")
    ProblemDetail.model_validate(response.json())


def test_timeout_problem_fixture(contract_json: Any) -> None:
    settings = ApiSettings(generate_timeout_seconds=0.001)

    def slow_generate(command: GenerateGeometryCommand):
        time.sleep(0.05)
        return generate_geometry(command)

    executor = TimedApplicationExecutor(settings=settings, generate_fn=slow_generate)
    with TestClient(
        create_app(settings=settings, executor=executor),
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/api/v1/generate",
            json=contract_json("generate-success.request.json"),
            headers={"X-Request-ID": "tutorboard-contract"},
        )
    assert response.status_code == 504
    assert response.json() == contract_json("operation-timeout.problem.json")


def test_internal_error_problem_fixture(contract_json: Any) -> None:
    settings = ApiSettings()

    def failing_generate(command: GenerateGeometryCommand):
        del command
        raise RuntimeError("SECRET INTERNAL FAILURE")

    executor = TimedApplicationExecutor(settings=settings, generate_fn=failing_generate)
    with TestClient(
        create_app(settings=settings, executor=executor),
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/api/v1/generate",
            json=contract_json("generate-success.request.json"),
            headers={"X-Request-ID": "tutorboard-contract"},
        )
    assert response.status_code == 500
    assert response.json() == contract_json("internal-error.problem.json")
    assert "SECRET" not in response.text
