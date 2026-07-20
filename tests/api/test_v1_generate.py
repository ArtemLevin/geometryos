from typing import Any

import pytest

ALTITUDE_PROMPT = "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."


def _request(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "input_type": "text",
        "input": ALTITUDE_PROMPT,
        "output": ["svg"],
        "mode": "strict",
    }
    payload.update(overrides)
    return payload


def test_generate_v1_success_contract(client: Any) -> None:
    response = client.post("/api/v1/generate", json=_request())

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["schema_version"] == "0.2.0"
    assert data["gir"]["schema_version"] == "0.2.0"
    assert data["validation_report"]["is_valid"] is True
    assert "<svg" in data["svg"]
    assert data["tikz"] is None
    assert data["warnings"] == []
    assert data["ambiguities"] == []


def test_generate_v1_without_outputs(client: Any) -> None:
    response = client.post("/api/v1/generate", json=_request(output=[]))

    assert response.status_code == 200
    data = response.json()
    assert data["svg"] is None
    assert data["tikz"] is None


def test_generate_v1_with_both_outputs(client: Any) -> None:
    response = client.post(
        "/api/v1/generate",
        json=_request(output=["svg", "tikz"]),
    )

    assert response.status_code == 200
    data = response.json()
    assert "<svg" in data["svg"]
    assert "\\begin{tikzpicture}" in data["tikz"]


def test_generate_v1_clarification_is_domain_result(client: Any) -> None:
    response = client.post(
        "/api/v1/generate",
        json=_request(input="Постройте треугольник ABC. Проведите биссектрису."),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["schema_version"] == "0.2.0"
    assert data["gir"] is None
    assert data["validation_report"] is None
    assert data["svg"] is None
    assert data["tikz"] is None
    assert data["ambiguities"][0]["code"] == "missing_angle"


def test_generate_v1_unsupported_is_structured_domain_error(client: Any) -> None:
    response = client.post(
        "/api/v1/generate",
        json=_request(input="Постройте невозможную конструкцию с магическим квадратом."),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["gir"] is None
    assert data["warnings"] == [
        {
            "code": "unsupported_construction",
            "message": "Construction is not supported.",
        }
    ]


@pytest.mark.parametrize(
    "payload",
    [
        _request(input=""),
        _request(input="   "),
        _request(input="x" * 20_001),
        _request(output=["svg", "svg"]),
        _request(output=["tikz", "tikz"]),
        _request(output=["pdf"]),
        _request(mode="draft"),
        {**_request(), "unknown": True},
        {"input": ALTITUDE_PROMPT},
    ],
)
def test_generate_v1_rejects_invalid_contract_payloads(
    client: Any,
    payload: dict[str, Any],
) -> None:
    response = client.post("/api/v1/generate", json=payload)
    assert response.status_code == 422
