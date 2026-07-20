from typing import cast

from fastapi import Request

from gir_api.errors import InputTooLargeError
from gir_api.execution import TimedApplicationExecutor
from gir_api.settings import ApiSettings


def get_executor(request: Request) -> TimedApplicationExecutor:
    return cast(TimedApplicationExecutor, request.app.state.application_executor)


def get_runtime_settings(request: Request) -> ApiSettings:
    return cast(ApiSettings, request.app.state.settings)


def enforce_input_limit(value: str, settings: ApiSettings) -> None:
    actual_chars = len(value)
    if actual_chars > settings.max_input_chars:
        raise InputTooLargeError(actual_chars=actual_chars, max_chars=settings.max_input_chars)
