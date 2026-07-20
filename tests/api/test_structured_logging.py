import io
import json
import logging
from typing import Any

from gir_api.constants import API_LOGGER_NAME, REQUEST_ID_HEADER
from gir_api.logging import JsonLogFormatter


def test_request_completion_log_is_structured_and_private(client: Any) -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger(API_LOGGER_NAME)
    logger.addHandler(handler)
    prompt = "PRIVATE-PROMPT-Постройте треугольник ABC"
    try:
        response = client.post(
            "/api/v1/generate",
            headers={REQUEST_ID_HEADER: "log-123"},
            json={
                "input_type": "text",
                "input": prompt,
                "output": [],
                "mode": "strict",
            },
        )
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 200
    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    completed = [item for item in records if item["event"] == "request_completed"]
    assert len(completed) == 1
    record = completed[0]
    assert record["request_id"] == "log-123"
    assert record["operation"] == "generate"
    assert record["status_code"] == 200
    assert record["duration_ms"] >= 0
    assert prompt not in stream.getvalue()
    assert "<svg" not in stream.getvalue()
