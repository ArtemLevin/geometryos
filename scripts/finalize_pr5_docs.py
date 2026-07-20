from pathlib import Path


def append_once(path: str, marker: str, section: str) -> None:
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8")
    if marker not in content:
        file_path.write_text(content.rstrip() + "\n\n" + section.strip() + "\n", encoding="utf-8")


readme = Path("README.md")
readme_content = readme.read_text(encoding="utf-8")
needle = "See `docs/contracts/API_CONTRACT.md` and `docs/adr/ADR-003-stable-http-api-v1.md`."
replacement = needle + "\n\nAPI resilience adds `X-Request-ID`, operation-specific soft timeouts, sanitized `application/problem+json` failures and structured JSON request logs. Runtime settings use the `GEOMETRYOS_*` environment variables documented in `docs/operations/API_RUNTIME.md`; the architectural decision is recorded in `docs/adr/ADR-004-api-resilience-boundary.md`."
if replacement not in readme_content:
    readme.write_text(readme_content.replace(needle, replacement), encoding="utf-8")

append_once(
    "docs/contracts/API_CONTRACT.md",
    "## Runtime resilience",
    """
## Runtime resilience

Every HTTP response carries `X-Request-ID`. Valid caller-provided identifiers are echoed; invalid or missing values are replaced with a generated UUID.

Infrastructure failures under `/api/v1` use `application/problem+json`. The stable runtime status matrix adds:

| Situation | HTTP | Code |
|---|---:|---|
| Configured operational input limit exceeded | 413 | `input_too_large` |
| Request or structural GIR validation failed | 422 | `request_validation_failed` |
| Semantic-invalid GIR sent to render | 422 | `semantic_validation_failed` |
| Operation deadline exceeded | 504 | `operation_timeout` |
| Unexpected internal failure | 500 | `internal_error` |

Successful and domain-result response DTOs remain unchanged. Legacy aliases retain their pre-v1 JSON bodies. Timeouts are soft: the API stops waiting, while an abandoned side-effect-free worker thread may finish later. See `docs/operations/API_RUNTIME.md`.
""",
)

append_once(
    "docs/COMPATIBILITY.md",
    "## Runtime failure compatibility",
    """
## Runtime failure compatibility

Stable `/api/v1` infrastructure failures use Problem Details with stable `code` and `request_id` fields. Successful payloads and expected domain results remain governed by the API v1 DTOs. Unversioned aliases preserve their existing JSON bodies, with the additive `X-Request-ID` response header.

Changing a Problem Details code, removing request correlation or changing a published HTTP status requires a documented API compatibility review.
""",
)

append_once(
    "CODEREVIEW_SKILL.md",
    "## API resilience review checklist",
    """
## API resilience review checklist

- Confirm every response receives `X-Request-ID` and request context is reset.
- Confirm v1 transport failures use sanitized Problem Details and legacy JSON shapes remain compatible.
- Confirm timeout logic exists only in `gir_api.execution` and does not enter `gir_core` or `gir_application`.
- Confirm logs contain metadata only: never prompts, GIR, rendered output, secrets or exception messages.
- Confirm successful API v1 response DTOs, GIR schema artifacts and render benchmarks remain unchanged.
""",
)
