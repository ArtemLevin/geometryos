from typing import Final

API_TITLE: Final = "GeometryOS API"
API_V1_PREFIX: Final = "/api/v1"
API_V1_VERSION: Final = "1.0.0"
MAX_GENERATE_INPUT_CHARS: Final = 20_000
REQUEST_ID_HEADER: Final = "X-Request-ID"
INTERNAL_ERROR_CODE_HEADER: Final = "X-GeometryOS-Error-Code"
PROBLEM_MEDIA_TYPE: Final = "application/problem+json"
API_LOGGER_NAME: Final = "geometryos.api"

OPENAPI_TAGS: Final = [
    {
        "name": "Generation",
        "description": "Create canonical GIR from supported input.",
    },
    {
        "name": "Validation",
        "description": "Validate GIR structure and semantics.",
    },
    {
        "name": "Rendering",
        "description": "Render validated canonical GIR.",
    },
    {
        "name": "Service",
        "description": "Service health endpoints.",
    },
]
