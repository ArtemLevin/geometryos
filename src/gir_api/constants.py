from typing import Final

API_TITLE: Final = "GeometryOS API"
API_V1_PREFIX: Final = "/api/v1"
API_V1_VERSION: Final = "1.0.0"
MAX_GENERATE_INPUT_CHARS: Final = 20_000

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
