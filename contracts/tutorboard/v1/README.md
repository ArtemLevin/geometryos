# TutorBoard consumer contract v1

This directory contains executable request and response fixtures for the stable GeometryOS HTTP API v1. The base URL is intentionally not fixed; TutorBoard supplies the deployment address.

`schemas/openapi.v1.json` is the machine-readable source for generated clients. These fixtures prove concrete behavior for generation success, ambiguity, unsupported constructions, canonical and legacy GIR validation, SVG/TikZ rendering, Problem Details, liveness, and readiness.

Every infrastructure error carries `request_id`; contract error fixtures use `tutorboard-contract`. Expected domain outcomes (`needs_clarification` and unsupported constructions) remain HTTP 200. GIR 0.1 input is read-only compatibility input and is returned as canonical GIR 0.2.

Update procedure:

```bash
uv run python scripts/export_openapi.py
uv run python scripts/export_tutorboard_contracts.py
make verify
npm ci --prefix contracts/tutorboard/typescript
npm run --prefix contracts/tutorboard/typescript generate
npm run --prefix contracts/tutorboard/typescript typecheck
```

Generated TypeScript types are intentionally not committed. The OpenAPI artifact, exact generator versions, and compilation smoke are the reproducible contract.
