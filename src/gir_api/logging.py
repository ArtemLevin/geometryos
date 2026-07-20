import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gir_api.constants import API_LOGGER_NAME
from gir_api.settings import ApiSettings

_MANAGED_HANDLER_ATTRIBUTE = "_geometryos_managed_handler"
_LOG_FIELDS = (
    "event",
    "request_id",
    "operation",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "error_code",
    "exception_type",
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        for field in _LOG_FIELDS:
            if field == "event":
                continue
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info and record.exc_info[2] is not None:
            payload["traceback"] = [
                {
                    "file": Path(frame.filename).name,
                    "line": frame.lineno,
                    "function": frame.name,
                }
                for frame in traceback.extract_tb(record.exc_info[2])
            ]

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(settings: ApiSettings) -> logging.Logger:
    logger = logging.getLogger(API_LOGGER_NAME)
    logger.setLevel(settings.log_level)
    logger.propagate = False

    managed = next(
        (
            handler
            for handler in logger.handlers
            if getattr(handler, _MANAGED_HANDLER_ATTRIBUTE, False)
        ),
        None,
    )
    if managed is None:
        managed = logging.StreamHandler(sys.stdout)
        setattr(managed, _MANAGED_HANDLER_ATTRIBUTE, True)
        logger.addHandler(managed)

    managed.setLevel(settings.log_level)
    managed.setFormatter(JsonLogFormatter())
    return logger


def get_api_logger() -> logging.Logger:
    return logging.getLogger(API_LOGGER_NAME)
