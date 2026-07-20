from pathlib import Path

path = Path("README.md")
text = path.read_text(encoding="utf-8")

replacements = {
    "API resilience adds `X-Request-ID`, operation-specific soft timeouts, sanitized `application/problem+json` failures and structured JSON request logs. Runtime settings use the `GEOMETRYOS_*` environment variables documented in `docs/operations/API_RUNTIME.md`; the architectural decision is recorded in `docs/adr/ADR-004-api-resilience-boundary.md`.\n": "API resilience adds `X-Request-ID`, operation-specific soft timeouts, sanitized `application/problem+json` failures and structured JSON request logs. Runtime settings use the `GEOMETRYOS_*` environment variables documented in `docs/operations/API_RUNTIME.md`; the architectural decision is recorded in `docs/adr/ADR-004-api-resilience-boundary.md`.\n\n## Published TutorBoard contract\n\n`schemas/openapi.v1.json` is the deterministic, committed API v1 contract. `contracts/tutorboard/v1` contains executable request and response fixtures, and `contracts/tutorboard/typescript` proves that a strict TypeScript client can be generated from the OpenAPI artifact. OpenAPI and fixture freshness are part of `make verify`; pull-request CI also detects breaking changes against the base branch.\n\n```bash\nmake openapi-check\nmake consumer-contract\nmake consumer-typescript\n```\n\nSee `contracts/tutorboard/v1/README.md` and `docs/adr/ADR-006-published-openapi-and-consumer-contract.md`.\n",
    "- GIR schema freshness checks;\n- benchmark suites;": "- GIR schema freshness checks;\n- OpenAPI v1 and TutorBoard fixture freshness checks;\n- benchmark suites;",
    "uv run python scripts/export_schema.py --check --output schemas/gir-0.2.schema.json\nuv run python scripts/run_benchmarks.py": "uv run python scripts/export_schema.py --check --output schemas/gir-0.2.schema.json\nuv run python scripts/export_openapi.py --check\nuv run python scripts/export_tutorboard_contracts.py --check\nuv run python scripts/run_benchmarks.py",
    "make schema-check\nmake api": "make schema-check\nmake openapi-check\nmake consumer-contract\nmake consumer-typescript\nmake api",
    "GitHub Actions runs three gated jobs on pushes and pull requests:\n\n- `verify` installs dependencies from `uv.lock` and runs `make verify`;\n- `package-smoke` independently builds and installs the wheel with `make package-smoke`;\n- `container-smoke` runs after both jobs, validates Compose, builds the hardened image and checks runtime security, probes, stable API behavior and graceful shutdown.\n": "GitHub Actions runs four gated jobs on pushes and pull requests:\n\n- `verify` installs dependencies from `uv.lock`, runs `make verify`, and checks OpenAPI compatibility with the base branch;\n- `package-smoke` independently builds and installs the wheel with `make package-smoke`;\n- `consumer-contract` executes TutorBoard fixtures, generates TypeScript types, and type-checks the smoke client;\n- `container-smoke` validates Compose, builds the hardened image and checks runtime security, probes, stable API behavior and graceful shutdown.\n",
    "stable API v1, readiness/liveness probes, a hardened container deployment, CLI contracts": "stable API v1, a published OpenAPI/TutorBoard consumer contract, readiness/liveness probes, a hardened container deployment, CLI contracts",
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"README anchor not found: {old[:80]!r}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
