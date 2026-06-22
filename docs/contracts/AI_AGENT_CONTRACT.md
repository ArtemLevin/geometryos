# AI Agent Contract

## Purpose
Define the contract for AI-assisted development and AI adapter behavior in the GIR project.
AI may accelerate implementation, parsing, documentation and review, but it must preserve GIR as the source of truth and keep architecture decisions auditable.

## Input
AI-facing inputs may include:

- user text that an adapter converts into draft GIR;
- existing GIR JSON or Pydantic models;
- codebase context, specs, benchmark fixtures and validation reports;
- human instructions about architecture, tests, contracts and documentation.

## Output
AI-produced outputs must be explicit and machine-checkable where possible:

- draft GIR plus confidence, ambiguity reports, warnings and explanation;
- code changes that preserve layer boundaries;
- tests or benchmark fixtures for new behavior;
- documentation updates when contracts or architecture semantics change.

## Invariants
- GIR is the source of truth.
- Layers do not bypass validation.
- Renderers never call AI.
- AI adapters do not render SVG, TikZ, PDF or images directly.
- AI-generated draft GIR must pass Pydantic parsing and semantic validation before rendering.
- Agent changes must not hide failing behavior by weakening tests or benchmark expectations.

## Decision comments
AI agents must leave concise code comments in controversial or non-obvious implementation points where a future maintainer could reasonably ask “why this path and not another?”.

Examples that require a comment:

- deliberate stubs or no-op extension points;
- hard-coded MVP data or coordinates;
- duplicated logic chosen to preserve packaging or layer boundaries;
- soft comparisons instead of exact comparisons;
- rejecting a more powerful dependency, solver, LLM integration or abstraction;
- validation or normalization order that protects a trust boundary.

The comment must explain the tradeoff and the rejected alternative in practical terms. It should not restate what the code already says.

Good example:

```python
# Design note: benchmark comparison is a soft subset check for now. It protects
# the public contract while allowing harmless future derived construction artifacts.
```

Bad example:

```python
# Run validation.
```

## Failure modes
- Invalid schema.
- Missing references.
- Ambiguous user intent.
- AI output bypasses GIR and renders directly.
- Code changes introduce hidden cross-layer dependencies.
- Non-obvious implementation tradeoffs are left undocumented.

## Minimal JSON example
```json
{"version":"0.1","scene_type":"2d","objects":[],"constraints":[],"construction_steps":[]}
```
