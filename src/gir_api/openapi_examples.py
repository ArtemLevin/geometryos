from typing import Any

ALTITUDE_GIR_EXAMPLE: dict[str, Any] = {
    "schema_version": "0.2.0",
    "scene_type": "2d",
    "objects": [
        {"id": "A", "type": "point", "label": "A"},
        {"id": "B", "type": "point", "label": "B"},
        {"id": "C", "type": "point", "label": "C"},
        {"id": "H", "type": "point", "label": "H"},
        {"id": "BC", "type": "segment", "points": ["B", "C"]},
        {"id": "AH", "type": "segment", "points": ["A", "H"]},
        {"id": "ABC", "type": "triangle", "vertices": ["A", "B", "C"]},
    ],
    "constraints": [
        {
            "id": "c_noncol_abc",
            "type": "non_collinear",
            "points": ["A", "B", "C"],
        },
        {
            "id": "c_altitude_a_bc",
            "type": "altitude",
            "from_point": "A",
            "to_object": "BC",
            "foot": "H",
            "segment": "AH",
        },
    ],
    "construction_steps": [
        {
            "id": "step_construct_triangle",
            "action": "construct_triangle",
            "objects": ["A", "B", "C", "BC", "ABC"],
            "constraints": ["c_noncol_abc"],
            "reason": "Construct triangle ABC.",
        },
        {
            "id": "step_construct_altitude",
            "action": "construct_altitude",
            "objects": ["H", "AH"],
            "constraints": ["c_altitude_a_bc"],
            "reason": "Construct altitude from A to BC.",
        },
    ],
    "metadata": {},
}

VALIDATION_REPORT_EXAMPLE: dict[str, Any] = {
    "is_valid": True,
    "issues": [],
    "warnings": [],
}

GENERATE_REQUEST_EXAMPLE: dict[str, Any] = {
    "input_type": "text",
    "input": "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
    "output": ["svg"],
    "mode": "strict",
}

GENERATE_SUCCESS_EXAMPLE: dict[str, Any] = {
    "status": "success",
    "confidence": 0.98,
    "schema_version": "0.2.0",
    "gir": ALTITUDE_GIR_EXAMPLE,
    "validation_report": VALIDATION_REPORT_EXAMPLE,
    "svg": '<svg xmlns="http://www.w3.org/2000/svg">...</svg>',
    "tikz": None,
    "warnings": [],
    "ambiguities": [],
    "explanation": "Rule-based altitude case.",
}

GENERATE_CLARIFICATION_EXAMPLE: dict[str, Any] = {
    "status": "needs_clarification",
    "confidence": 0.4,
    "schema_version": "0.2.0",
    "gir": None,
    "validation_report": None,
    "svg": None,
    "tikz": None,
    "warnings": [],
    "ambiguities": [
        {
            "code": "missing_angle",
            "message": "Не указано, биссектрису какого угла нужно построить.",
            "options": ["angle_A", "angle_B", "angle_C"],
        }
    ],
    "explanation": "Bisector request lacks angle target.",
}

GENERATE_UNSUPPORTED_EXAMPLE: dict[str, Any] = {
    "status": "error",
    "confidence": 0.0,
    "schema_version": "0.2.0",
    "gir": None,
    "validation_report": None,
    "svg": None,
    "tikz": None,
    "warnings": [
        {
            "code": "unsupported_construction",
            "message": "Construction is not supported.",
        }
    ],
    "ambiguities": [],
    "explanation": "No supported construction matched the input.",
}

VALIDATE_RESPONSE_EXAMPLE: dict[str, Any] = {
    "schema_version": "0.2.0",
    "canonical_gir": ALTITUDE_GIR_EXAMPLE,
    "validation_report": VALIDATION_REPORT_EXAMPLE,
}

RENDER_SVG_RESPONSE_EXAMPLE: dict[str, Any] = {
    "schema_version": "0.2.0",
    "media_type": "image/svg+xml",
    "content": '<svg xmlns="http://www.w3.org/2000/svg">...</svg>',
}

RENDER_TIKZ_RESPONSE_EXAMPLE: dict[str, Any] = {
    "schema_version": "0.2.0",
    "media_type": "text/x-tex",
    "content": "\\begin{tikzpicture}...\\end{tikzpicture}",
}

REQUEST_VALIDATION_PROBLEM_EXAMPLE: dict[str, Any] = {
    "type": "urn:geometryos:problem:request-validation",
    "title": "Request validation failed",
    "status": 422,
    "detail": "The request payload does not satisfy the API contract.",
    "instance": "/api/v1/generate",
    "code": "request_validation_failed",
    "request_id": "tutorboard-contract",
    "errors": [
        {
            "code": "literal_error",
            "message": "Input should be 'strict'",
            "location": ["body", "mode"],
        }
    ],
}

TIMEOUT_PROBLEM_EXAMPLE: dict[str, Any] = {
    "type": "urn:geometryos:problem:operation-timeout",
    "title": "Operation timed out",
    "status": 504,
    "detail": "The generate operation exceeded its configured time limit.",
    "instance": "/api/v1/generate",
    "code": "operation_timeout",
    "request_id": "tutorboard-contract",
    "errors": [],
}

INTERNAL_ERROR_PROBLEM_EXAMPLE: dict[str, Any] = {
    "type": "urn:geometryos:problem:internal-error",
    "title": "Internal server error",
    "status": 500,
    "detail": "An unexpected internal error occurred.",
    "instance": "/api/v1/generate",
    "code": "internal_error",
    "request_id": "tutorboard-contract",
    "errors": [],
}

HEALTH_RESPONSE_EXAMPLE = {"status": "ok"}
READINESS_RESPONSE_EXAMPLE = {
    "status": "ready",
    "checks": [
        {"name": "lifecycle", "status": "pass"},
        {"name": "settings", "status": "pass"},
        {"name": "executor", "status": "pass"},
    ],
}
