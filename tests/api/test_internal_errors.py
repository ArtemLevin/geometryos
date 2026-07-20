import io
import json
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gir_api.constants import API_LOGGER_NAME, REQUEST_ID_HEADER
from gir_api.execution import TimedApplicationExecutor
from gir_api.logging import JsonLogFormatter
from gir_api.settings import ApiSettings
from gir_application import GenerateGeometryCommand, GenerateGeometryResult


def test_internal_error_is_sanitized_and_correlated(app_factory: Any) -> None:
    settings = ApiSettings()
    secret = "SECRET-PROMPT-CONTENT C:\\Users\\Artem\\secret"

    def failing_generate(command: GenerateGeometryCommand) -> GenerateGeometryResult:
        del command
        raise RuntimeError(secret)

    app: FastAPI = app_factory(
        settings=settings,
        executor=TimedApplicationExecutor(settings=settings, generate_fn=failing_generate),
    )
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger(API_LOGGER_NAME)
    logger.addHandler(handler)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/generate",
                headers={REQUEST_ID_HEADER: "internal-123"},
                json={
                    "input_type": "text",
                    "input": "safe input",
                    "output": [],
                    "mode": "strict",
                },
            )
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 500
    assert response.headers[REQUEST_ID_HEADER] == "internal-123"
    assert response.json()["code"] == "internal_error"
    assert secret not in response.text
    assert "RuntimeError" not in response.text
    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    internal = next(item for item in records if item["event"] == "internal_error")
    assert internal["request_id"] == "internal-123"
    assert internal["exception_type"] == "RuntimeError"
    assert secret not in stream.getvalue()
