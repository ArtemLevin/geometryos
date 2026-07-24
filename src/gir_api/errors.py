from gir_api.context import ApiOperation
from gir_core.models.validation import ValidationReport


class ApiRuntimeError(Exception):
    code = "api_runtime_error"


class InputTooLargeError(ApiRuntimeError):
    code = "input_too_large"

    def __init__(self, *, actual_chars: int, max_chars: int) -> None:
        super().__init__("Input exceeds the configured operational limit.")
        self.actual_chars = actual_chars
        self.max_chars = max_chars


class OperationTimeoutError(ApiRuntimeError):
    code = "operation_timeout"

    def __init__(self, *, operation: ApiOperation, timeout_seconds: float) -> None:
        super().__init__(f"{operation.value} operation timed out.")
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class SemanticValidationError(ApiRuntimeError):
    code = "semantic_validation_failed"

    def __init__(self, validation_report: ValidationReport) -> None:
        super().__init__("GIR failed semantic validation.")
        self.validation_report = validation_report


class ServiceUnavailableError(ApiRuntimeError):
    code = "service_unavailable"

    def __init__(self) -> None:
        super().__init__("GeometryOS is not ready to accept application requests.")
