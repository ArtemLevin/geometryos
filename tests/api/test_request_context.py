from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID

from gir_api.constants import REQUEST_ID_HEADER


def test_missing_request_id_is_generated(client: Any) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    UUID(response.headers[REQUEST_ID_HEADER])


def test_valid_request_id_is_preserved(client: Any) -> None:
    response = client.get("/health", headers={REQUEST_ID_HEADER: "caller-123"})
    assert response.headers[REQUEST_ID_HEADER] == "caller-123"


def test_invalid_request_id_is_replaced(client: Any) -> None:
    response = client.get("/health", headers={REQUEST_ID_HEADER: "invalid request id"})
    assert response.headers[REQUEST_ID_HEADER] != "invalid request id"
    UUID(response.headers[REQUEST_ID_HEADER])


def test_problem_body_and_header_share_request_id(client: Any) -> None:
    response = client.post(
        "/api/v1/generate",
        headers={REQUEST_ID_HEADER: "validation-123"},
        json={"input_type": "text", "input": "", "mode": "strict"},
    )
    assert response.status_code == 422
    assert response.headers[REQUEST_ID_HEADER] == "validation-123"
    assert response.json()["request_id"] == "validation-123"


def test_parallel_request_contexts_are_isolated(client: Any) -> None:
    def request(request_id: str) -> str:
        response = client.get("/health", headers={REQUEST_ID_HEADER: request_id})
        return response.headers[REQUEST_ID_HEADER]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(request, ["request-a", "request-b"]))
    assert results == ["request-a", "request-b"]
