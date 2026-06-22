---
name: geometryos
description: StrictTail development protocol for GeometryOS tasks; use when changing GeometryOS code, docs, schema, validation, benchmarks, API, renderers, layout, AI adapter behavior, or agent rules.
---

# GeometryOS StrictTail Protocol

## Purpose

This protocol defines how an AI development agent must work inside GeometryOS.

GeometryOS is a GIR-first geometry compiler. The goal is not to write more code. The goal is to make the smallest safe change that preserves GIR contracts, semantic validation, benchmarks, API behavior, and rendering discipline.

This protocol combines two ideas:

1. **Minimality discipline**: do not build unnecessary abstractions, dependencies, layers, or speculative features.
2. **Diagnostic discipline**: measure complexity and architectural damage before and after non-trivial changes.

The agent must optimize for correctness, small diffs, explicit contracts, and measurable project health.

---

# 1. Core project invariants

These rules are always active.

## 1.1. GIR is the source of truth

The LLM is never the source of truth.

Correct pipeline:

```text
User input
  ↓
AI adapter / parser
  ↓
draft GIR
  ↓
schema validation
  ↓
semantic validation
  ↓
normalization
  ↓
layout
  ↓
SVG / TikZ / API response
```

Forbidden pipeline:

```text
User input → LLM → SVG
User input → LLM → TikZ
User input → LLM → PDF
User input → renderer without validation
```

## 1.2. Geometry core must remain pure

`gir_core` must not depend on:

```text
FastAPI
frontend
database
Docker
OpenAI
Ollama
LLM SDK
SVG renderer
TikZ renderer
CLI
```

`gir_core` may contain:

```text
Pydantic models
GIR schema generation
semantic validation
normalization
layout-independent domain logic
```

## 1.3. AI adapter creates draft GIR only

`gir_ai` may:

```text
parse text;
return draft GIR;
return confidence;
return ambiguities;
return warnings;
return explanation.
```

`gir_ai` must not:

```text
render SVG;
render TikZ;
bypass validation;
silently guess ambiguity;
mutate validated GIR.
```

## 1.4. Renderer draws already-valid scenes

`gir_render` may:

```text
draw SVG;
draw TikZ;
consume validated GIR or LayoutScene.
```

`gir_render` must not:

```text
fix geometry;
invent missing objects;
call LLM;
ignore semantic validation;
silently render invalid GIR.
```

## 1.5. Ambiguity is a first-class response

If a request is ambiguous, the system must return a structured clarification response, not guess.

Example:

```json
{
  "status": "needs_clarification",
  "ambiguities": [
    {
      "code": "missing_angle",
      "message": "Не указано, биссектрису какого угла нужно построить.",
      "options": ["angle_A", "angle_B", "angle_C"]
    }
  ]
}
```

---

# 2. Minimality ladder

Before coding, the agent must walk this ladder.

For each task, ask in order:

```text
1. Can this be avoided?
2. Can this be solved by documentation or contract clarification?
3. Can this be solved by adding or improving a benchmark?
4. Can this be solved by schema validation?
5. Can this be solved by semantic validation?
6. Can this be solved by extending existing code?
7. Can this be solved with Python stdlib?
8. Can this be solved with an already installed dependency?
9. Can this be solved with one small helper?
10. Only then create a new module, layer, dependency, or abstraction.
```

The agent must not add a new abstraction for one implementation.

The agent must not add a new dependency without explicit justification.

The agent must prefer deletion, simplification, and direct code over speculative framework design.

---

# 3. GeometryOS-specific minimality ladder

For GeometryOS tasks, use this stricter ladder:

```text
1. Can a benchmark expose the desired behavior?
2. Can the GIR schema express it already?
3. Can the semantic validator enforce it?
4. Can normalize_gir handle it?
5. Can current renderer/layout be extended minimally?
6. Can current API response model be extended without a new route?
7. Can a rule-based adapter handle it before LLM integration?
8. Can this be deferred behind a geometryos: debt comment?
9. Only then add a new subsystem.
```

Do not introduce:

```text
full geometry solver;
OpenCV sketch parser;
real LLM integration;
database;
auth;
frontend framework;
plugin system;
event bus;
microservices;
Docker;
```

unless the task explicitly requires it and the current MVP has already passed contract, benchmark, and validation checks.

---

# 4. Diagnostic protocol

For non-trivial changes, the agent must diagnose before coding.

## 4.1. Small change

For small changes:

```bash
uv run pytest
uv run python scripts/run_benchmarks.py
```

## 4.2. Normal change

For normal changes:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/export_schema.py --check
uv run python scripts/run_benchmarks.py
```

## 4.3. Architectural change

For architectural changes:

```bash
uv run python scripts/verify.py
strictacode analyze . --details --format json --top-packages 5 --top-modules 5 --top-classes 10 --top-methods 15 --top-functions 15
```

If a baseline report exists:

```bash
strictacode compare baseline.json current.json
```

If strictacode is not installed, the agent must say so and continue with GeometryOS-native checks.

---

# 5. When strictacode is required

Strictacode is optional for small MVP work.

Strictacode is recommended for:

```text
large refactors;
new modules;
new architecture layers;
new dependencies;
new service boundaries;
large validator rewrites;
large renderer rewrites;
before/after PR health comparison;
periodic repository audit.
```

Strictacode is not required for:

```text
README edits;
small test additions;
single benchmark case;
minor typo fix;
small schema wording changes;
small rule-based adapter fix.
```

---

# 6. Forbidden shortcuts

The agent must never do the following:

```text
LLM → SVG
LLM → TikZ
LLM → PDF
Renderer without validation
Schema change without schema export/check
GIR semantic change without GIR_SPEC update
API response change without API tests
New behavior without benchmark coverage
New dependency without justification
New abstraction for a single implementation
Silent ambiguity guessing
```

---

# 7. Required checks by touched area

## 7.1. If GIR models changed

Run:

```bash
uv run python scripts/export_schema.py
uv run python scripts/export_schema.py --check
uv run pytest tests/test_schema_export.py
uv run pytest tests/test_gir_models.py
```

Also update:

```text
docs/GIR_SPEC.md
schemas/gir.schema.json
benchmarks if behavior changed
```

## 7.2. If semantic validator changed

Run:

```bash
uv run pytest tests/test_semantic_validation.py
uv run python scripts/run_benchmarks.py
```

Add negative tests for invalid references and invalid object types.

## 7.3. If AI adapter changed

Run:

```bash
uv run pytest tests/test_benchmarks.py
uv run python scripts/run_benchmarks.py
```

Ensure ambiguous cases return `needs_clarification`.

Do not make adapter render output.

## 7.4. If API changed

Run:

```bash
uv run pytest tests/test_api_generate.py
uv run pytest
```

Update:

```text
docs/contracts/API_CONTRACT.md
README.md examples if response shape changed
```

## 7.5. If renderer/layout changed

Run:

```bash
uv run pytest tests/test_svg_renderer.py
uv run pytest tests/test_tikz_renderer.py
uv run pytest tests/test_layout.py
uv run python scripts/run_benchmarks.py
```

Renderer must not render invalid GIR.

## 7.6. If benchmark runner changed

Run:

```bash
uv run python scripts/run_benchmarks.py
uv run pytest tests/test_benchmarks.py
```

CLI and script must use the same benchmark runner.

---

# 8. Intentional debt comments

If the agent intentionally leaves a simplified implementation, it must mark it.

Use:

```python
# geometryos: short explanation of intentional simplification
# ceiling: when this becomes unacceptable
# trigger: event that requires replacement
```

Example:

```python
# geometryos: naive ABC/H/M layout only
# ceiling: replace after 10 render benchmark cases
# trigger: first benchmark with non-ABC triangle labels
```

Intentional debt must be:

```text
visible;
specific;
bounded;
connected to an upgrade trigger.
```

The agent must not hide debt in vague TODO comments.

---

# 9. PR planning protocol

Before implementation, the agent must produce a short plan:

```markdown
## Task classification

bugfix | feature | refactor | schema change | API change | benchmark change | docs-only

## Minimality decision

Why this cannot be solved with docs/schema/validator/benchmark only.

## Files expected to change

- ...

## Files explicitly not touched

- ...

## Required checks

- ...
```

---

# 10. PR report protocol

Every PR must end with:

```markdown
## Summary

What changed.

## Minimality check

- [ ] YAGNI considered
- [ ] Existing code reused
- [ ] No unnecessary dependency added
- [ ] No unnecessary abstraction added
- [ ] No validation/benchmark/schema shortcut taken

## GeometryOS contract check

- [ ] GIR remains source of truth
- [ ] AI adapter returns draft GIR only
- [ ] Renderer does not bypass validation
- [ ] Ambiguity is explicit
- [ ] Schema updated if needed
- [ ] Benchmarks updated if needed

## Verification

- [ ] uv run ruff check .
- [ ] uv run ruff format --check .
- [ ] uv run mypy src
- [ ] uv run pytest
- [ ] uv run python scripts/export_schema.py --check
- [ ] uv run python scripts/run_benchmarks.py
- [ ] uv run python scripts/verify.py
- [ ] strictacode analyze . --details --format json

## Strictacode summary

Only fill this section if strictacode was run.

- score:
- refactoring pressure:
- overengineering pressure:
- complexity density:
- hotspots:

## Intentional debt

- ...
```

Do not mark a check as passed unless it was actually run.

If a command was not run, write:

```text
not run
```

---

# 11. Operating modes

## Lite mode

Use for tiny changes.

```text
Targeted tests only.
No strictacode required.
No architectural rewrite.
```

## Full mode

Default mode.

```text
Run GeometryOS verification.
Update tests/docs/schema if needed.
Use minimality ladder.
```

## Strict mode

Use for architectural changes.

```text
Run strictacode before and after.
Compare metrics if baseline exists.
Require full verification.
Require explicit PR report.
```

## Off mode

Only if the user explicitly disables the protocol.

Even in off mode, do not violate core project invariants.

---

# 12. Final rule

The correct GeometryOS change is not the most impressive change.

The correct change is:

```text
smallest safe diff
  +
valid GIR contract
  +
semantic validation
  +
benchmark coverage
  +
clear API behavior
  +
no unnecessary architecture
```
