from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gir_api.settings import ApiSettings


def test_operational_input_limit_returns_413_problem(app_factory: Any) -> None:
    app: FastAPI = app_factory(settings=ApiSettings(max_input_chars=10))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/generate",
            json={
                "input_type": "text",
                "input": "12345678901",
                "output": [],
                "mode": "strict",
            },
        )
    assert response.status_code == 413
    assert response.json()["code"] == "input_too_large"
    assert "12345678901" not in response.text


def test_legacy_operational_limit_keeps_legacy_error_shape(app_factory: Any) -> None:
    app: FastAPI = app_factory(settings=ApiSettings(max_input_chars=10))
    with TestClient(app) as client:
        response = client.post(
            "/generate",
            json={
                "input_type": "text",
                "input": "12345678901",
                "output": [],
                "mode": "strict",
            },
        )
    assert response.status_code == 413
    assert response.json() == {"detail": "Input exceeds the configured limit."}
