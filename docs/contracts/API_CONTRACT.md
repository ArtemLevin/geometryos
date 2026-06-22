# API Contract

## Purpose
Define the public HTTP contract for the GIR Geometry Compiler API.
The API exposes the same GIR-first pipeline as the CLI: text is converted to draft GIR, validated, normalized, validated again and only then rendered.

## Input
Primary endpoints:

- `GET /health` accepts no body.
- `POST /generate` accepts text input and requested render outputs.
- `POST /validate-gir` accepts GIR JSON.
- `POST /render/svg` and `POST /render/tikz` accept GIR JSON.

Minimal `/generate` request:

```json
{
  "input_type": "text",
  "input": "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
  "output": ["svg", "tikz"],
  "mode": "strict"
}
```

## Output
`/generate` always returns a domain-level status rather than guessing silently:

- `success` means GIR exists, validation passed and requested renders may be present.
- `needs_clarification` means user intent is ambiguous; this is not a server error.
- `error` means the adapter could not produce usable GIR or validation failed.

The response includes:

- `status`
- `confidence`
- `gir`
- `validation_report`
- `svg`
- `tikz`
- `warnings`
- `ambiguities`
- `explanation`

## Invariants
- GIR is the source of truth.
- Layers do not bypass validation.
- Renderers never call AI.
- Ambiguity is returned as structured domain data, not hidden as a generic error.
- Render endpoints reject semantic-invalid GIR with HTTP 422 instead of drawing it.

## Failure modes
- Pydantic-invalid requests or structurally invalid GIR payloads return HTTP 422.
- Pydantic-valid but semantic-invalid GIR sent to `/validate-gir` returns HTTP 200 with `is_valid: false` and populated `issues`.
- Pydantic-valid but semantic-invalid GIR sent to `/render/svg` or `/render/tikz` returns HTTP 422 with a validation report in `detail`.
- Ambiguous `/generate` input returns HTTP 200 with `status: "needs_clarification"`, `gir: null`, no rendered output and structured `ambiguities`.
- Unsupported `/generate` input returns HTTP 200 with `status: "error"`; this is a domain failure, not a server error.

## Minimal JSON example
Successful `/generate` response shape:

```json
{
  "status": "success",
  "confidence": 0.9,
  "gir": {},
  "validation_report": {"is_valid": true, "issues": [], "warnings": []},
  "svg": "<svg>...</svg>",
  "tikz": "\\begin{tikzpicture}...",
  "warnings": [],
  "ambiguities": [],
  "explanation": "Rule-based altitude MVP case."
}
```

Ambiguous `/generate` response shape:

```json
{
  "status": "needs_clarification",
  "confidence": 0.4,
  "gir": null,
  "validation_report": null,
  "svg": null,
  "tikz": null,
  "warnings": [],
  "ambiguities": [
    {
      "code": "missing_angle",
      "message": "Не указано, биссектрису какого угла нужно построить.",
      "options": ["angle_A", "angle_B", "angle_C"]
    }
  ],
  "explanation": "Bisector request lacks angle target."
}
```
