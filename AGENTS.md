# AI Agent Rules

1. First inspect the code and docs.
2. Plan before editing.
3. Preserve architecture layers: Text → AI Adapter → draft GIR → validation → normalized GIR → layout → render.
4. Never generate SVG/TikZ/PDF directly from an LLM.
5. Do not add agent behavior without updating `docs/contracts/AI_AGENT_CONTRACT.md`.
6. Do not change GIR semantics without updating `docs/GIR_SPEC.md` and schema/tests.
7. Do not fix tests to match a bug; fix the implementation or update the spec deliberately.
8. Run pytest, ruff, mypy, schema export and benchmarks after changes.

## GeometryOS StrictTail Protocol

For all non-trivial development tasks, follow `skills/geometryos/SKILL.md`.

Default mode: full.

Core rule: make the smallest safe change that preserves GIR schema, semantic validation, benchmarks, API contract and render validation gates.
