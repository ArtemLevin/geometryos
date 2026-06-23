# GeometryOS MVP Roadmap

## 1. MVP Definition

GeometryOS MVP is a small, deterministic, GIR-first geometry compiler. It accepts a limited set of school-geometry prompts, converts them into draft GIR, validates and normalizes that GIR, lays it out through a canonical MVP layout, and renders SVG/TikZ through validation-gated renderers.

Required MVP pipeline:

```text
Text → draft GIR → validation → normalization → layout → SVG/TikZ
```

GIR is the source of truth. The MVP is not a general geometry solver, not a free-form LLM drawing tool, and not a visual editor.

## 2. Product Scope

In the MVP, a user can:

1. Submit a simple Russian school-geometry construction prompt.
2. Receive a structured domain status: `success`, `needs_clarification`, or `error`.
3. Receive validated GIR for supported cases.
4. Receive a validation report for generated or submitted GIR.
5. Receive SVG output for valid supported scenes.
6. Receive TikZ output for valid supported scenes.
7. Receive structured ambiguity data for ambiguous requests.
8. Run the same GIR-first pipeline through API and CLI entrypoints.
9. Verify schema freshness and product contracts through scripts and benchmarks.

## 3. Current Implemented Surface

### Core

- Pydantic v2 GIR models for scenes, objects, constraints, layout and construction steps.
- Discriminated unions for GIR object and constraint types.
- JSON Schema export and freshness check through shared `gir_core.schema` helpers.
- Type-aware semantic validation for object references, constraint references and MVP construction roles.
- `normalize_gir` extension point in the validation pipeline.

### AI adapter

- Deterministic rule-based text-to-GIR adapter.
- Supported MVP prompt patterns:
  - triangle ABC;
  - altitude from A to BC;
  - median from A to BC;
  - midpoint M of BC;
  - angle bisector of angle A.
- Ambiguous bisector requests return `needs_clarification` with `missing_angle` ambiguity.
- Unsupported requests return `error` with no GIR instead of hallucinated geometry.

### Render and layout

- `LayoutScene` is the boundary between validated GIR and renderers.
- SVG and TikZ public render entrypoints validate `GirScene` before layout.
- Canonical MVP layout supports single-triangle scenes, arbitrary triangle labels by vertex order, midpoint constraints, median constraints and altitude foot projection.
- Render benchmark suites cover structural SVG/TikZ output checks.

### API

- `GET /health`.
- `POST /generate`.
- `POST /validate-gir`.
- `POST /render/svg`.
- `POST /render/tikz`.
- API tests cover success, ambiguity, unsupported input, validation reports and render rejection for semantic-invalid GIR.

### CLI

- `gir validate`.
- `gir render-svg`.
- `gir render-tikz`.
- `gir benchmark --root .`.
- `gir benchmark --benchmarks-dir ...`.
- `gir export-schema --output ...`.
- `gir export-schema --check --output ...`.

### Benchmarks

- `benchmarks/text_to_gir` covers success, ambiguity and explicit unsupported/error cases.
- `benchmarks/gir_to_svg` covers structural SVG render checks.
- `benchmarks/gir_to_tikz` covers structural TikZ render checks.
- `scripts/run_benchmarks.py` and `gir benchmark --root .` use the shared `gir_benchmarks` runner.

## 4. Missing Before MVP

- [ ] `uv run python scripts/verify.py` passes locally.
- [ ] `make verify` passes locally when `make` is available.
- [ ] CI passes on `main` with schema, tests and benchmarks.
- [ ] `uv run python scripts/export_schema.py --check` passes.
- [ ] `uv run python scripts/run_benchmarks.py` passes with `failed == 0`.
- [ ] `uv run gir benchmark --root .` passes with `failed == 0`.
- [ ] API contract tests pass for success, ambiguity, unsupported input, validation reports and render 422 cases.
- [ ] CLI smoke tests pass for validation, rendering, benchmark and schema commands.
- [ ] MVP Roadmap, README, architecture docs, API contract and benchmark contract agree on scope.
- [ ] Layout limitations remain documented with `geometryos:` debt comments.
- [ ] No duplicate benchmark runner or schema export logic remains.

## 5. Explicitly Out of MVP

The following are explicitly out of MVP:

- Real LLM integration.
- OpenAI, Ollama, LangChain or other LLM SDK dependency.
- Free-form NLP parser.
- OpenCV sketch recognition.
- SymPy-based geometry solver.
- General constraint solver.
- Arbitrary multi-figure layout optimization.
- Collision-aware label placement.
- Frontend or visual editor.
- PDF export.
- Authentication.
- Database.
- Docker deployment.
- Multi-user workspace.
- Plugin system.
- Event bus or microservice platform.
- Pixel-perfect visual rendering.

These are not rejected forever. They are deferred until the GIR-first compiler loop is stable and fully verified.

## 6. MVP Architecture Contract

MVP must preserve these boundaries:

1. `gir_core` has no FastAPI, renderer, LLM, database or frontend dependency.
2. `gir_ai` returns draft GIR, confidence, warnings, ambiguities and explanation only.
3. `gir_ai` never renders SVG, TikZ, PDF or images.
4. `gir_render` does not fix geometry, invent missing objects or call AI.
5. Public render entrypoints validate semantic correctness before layout/render.
6. Ambiguity is returned as structured domain data, not hidden as a server error.
7. JSON Schema is generated from Pydantic models.
8. Benchmarks are product contracts, not cosmetic examples.
9. CLI, API and scripts use shared core helpers where available.

Forbidden flows:

```text
Text → LLM → SVG
Text → LLM → TikZ
Text → LLM → PDF
Renderer → geometry correction
API → render without validation
CLI → hidden repo-root magic where explicit paths are available
```

## 7. MVP Acceptance Criteria

MVP is reached when all of the following are true.

### Verification

- [ ] `uv sync --dev` succeeds.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run ruff format --check .` passes.
- [ ] `uv run mypy src` passes.
- [ ] `uv run pytest` passes, including API, CLI and import smoke tests.
- [ ] `uv run python scripts/verify.py` passes as the main local quality gate.
- [ ] `make verify` passes, if Makefile is available.
- [ ] CI runs `uv run python scripts/verify.py` and passes on `main`.

### Schema

- [ ] `uv run python scripts/export_schema.py --check` passes.
- [ ] `uv run gir export-schema --check --output schemas/gir.schema.json` passes.
- [ ] `schemas/gir.schema.json` contains real `$defs` generated from the Pydantic models.
- [ ] Schema freshness is tested in CI or verifier scripts.

### Benchmarks

- [ ] `uv run python scripts/run_benchmarks.py` passes.
- [ ] `uv run gir benchmark --root .` passes.
- [ ] `uv run gir export-schema --check --output schemas/gir.schema.json` passes.
- [ ] `text_to_gir` suite has success, ambiguity and error cases.
- [ ] `gir_to_svg` suite passes.
- [ ] `gir_to_tikz` suite passes.
- [ ] Benchmark summary reports `failed == 0`.

### API

- [ ] `/health` returns stable health response.
- [ ] `/generate` success case returns GIR, validation report and requested SVG/TikZ.
- [ ] `/generate` ambiguous case returns HTTP 200 with `status: "needs_clarification"`.
- [ ] `/generate` unsupported case returns HTTP 200 with `status: "error"`.
- [ ] `/validate-gir` returns a validation report for Pydantic-valid GIR.
- [ ] `/validate-gir` returns `is_valid: false` for semantic-invalid but structurally valid GIR.
- [ ] `/render/svg` rejects semantic-invalid GIR with HTTP 422.
- [ ] `/render/tikz` rejects semantic-invalid GIR with HTTP 422.

### CLI

- [ ] `gir validate path/to/scene.gir.json` works.
- [ ] `gir render-svg path/to/scene.gir.json` works.
- [ ] `gir render-tikz path/to/scene.gir.json` works.
- [ ] `gir benchmark --root .` works.
- [ ] `gir benchmark --benchmarks-dir benchmarks/text_to_gir` works.
- [ ] `gir export-schema --check --output schemas/gir.schema.json` works.

## 8. Benchmark Targets

### text_to_gir

Minimum MVP cases:

Success:

- triangle only;
- altitude from A to BC;
- median from A to BC;
- midpoint M of BC;
- angle bisector of angle A.

Needs clarification:

- bisector without specified angle.

Error:

- unsupported square;
- unsupported circle;
- malformed request;
- unsupported parallel construction;
- unsupported perpendicular construction.

### gir_to_svg

Minimum MVP cases:

- triangle;
- altitude;
- median;
- arbitrary triangle labels.

### gir_to_tikz

Minimum MVP cases:

- triangle;
- altitude;
- median;
- arbitrary triangle labels.

Render benchmarks are structural checks. They should verify tags/commands, labels and minimum line/draw counts, not pixel-perfect visual output.

## 9. API Contract Targets

Domain statuses:

- `success`;
- `needs_clarification`;
- `error`.

HTTP behavior:

- Pydantic-invalid request → HTTP 422.
- Structurally invalid GIR payload → HTTP 422.
- Semantic-invalid GIR in `/validate-gir` → HTTP 200 with `is_valid: false`.
- Semantic-invalid GIR in `/render/svg` or `/render/tikz` → HTTP 422.
- Ambiguous `/generate` request → HTTP 200 with `status: "needs_clarification"`.
- Unsupported `/generate` request → HTTP 200 with `status: "error"`.

## 10. CLI Contract Targets

Required MVP commands:

```bash
gir validate path/to/scene.gir.json
gir render-svg path/to/scene.gir.json
gir render-tikz path/to/scene.gir.json
gir benchmark --root .
gir benchmark --benchmarks-dir benchmarks/text_to_gir
gir export-schema --check --output schemas/gir.schema.json
```

CLI commands must not rely on hidden repository-root magic when explicit `--root`, `--benchmarks-dir` or `--output` options are available.

## 11. Render/Layout Targets

MVP layout supports:

- single primary triangle scenes;
- arbitrary triangle labels by vertex order;
- midpoint constraints;
- median constraints via their midpoint;
- altitude foot projection onto the target segment;
- basic angle-bisector ray placement when the GIR already contains the required angle, ray and through-point objects.

MVP layout does not support:

- full constraint solving;
- multi-triangle optimization;
- collision avoidance;
- general circle rendering;
- arbitrary ray/line styling beyond MVP approximations;
- pixel-perfect visual output.

Renderers must stay serialization sinks: layout computes coordinates, renderers draw `LayoutScene`.

## 12. Documentation Targets

Before MVP, the following documents must agree:

- `README.md`;
- `docs/MVP_ROADMAP.md`;
- `docs/ARCHITECTURE.md`;
- `docs/GIR_SPEC.md`;
- `docs/contracts/API_CONTRACT.md`;
- `docs/contracts/BENCHMARK_CONTRACT.md`;
- `docs/contracts/AI_AGENT_CONTRACT.md`;
- `docs/contracts/RENDER_CONTRACT.md`;
- `AGENTS.md`;
- `skills/geometryos/SKILL.md`.

Documentation must not promise solver, frontend, LLM, sketch, PDF, database or platform features as MVP behavior.

## 13. Milestones

### Milestone A — Stable skeleton

Goal: verification is reliable and reproducible.

Acceptance:

- `scripts/verify.py` passes.
- CI passes.
- Schema freshness check passes.

### Milestone B — Contract MVP

Goal: schema, API and benchmark contracts are enforced.

Acceptance:

- API contract tests pass.
- Benchmark runner covers text and render suites.
- CLI uses shared benchmark and schema helpers.

### Milestone C — Render MVP

Goal: validated GIR renders to SVG/TikZ for MVP scenes.

Acceptance:

- SVG render benchmarks pass.
- TikZ render benchmarks pass.
- Canonical layout supports MVP scenes.

### Milestone D — Parser MVP

Goal: deterministic adapter supports basic school-geometry prompts.

Acceptance:

- Text-to-GIR success benchmarks pass.
- Ambiguity benchmark returns structured clarification.
- Unsupported benchmark cases return `error` without GIR.

### Milestone E — MVP candidate

Goal: the service can be demonstrated end-to-end.

Acceptance:

- User prompt → GIR → validation report → SVG/TikZ works through API and CLI.
- Full verifier and CI are green.

## 14. PR Sequence

### PR 1 — Single source of truth for benchmarks

Extract benchmark runner into `src/gir_benchmarks` and remove duplicate benchmark logic.

### PR 2 — CLI root/output options

Make benchmark and schema CLI commands explicit and reproducible with `--root`, `--benchmarks-dir` and `--output`.

### PR 3 — Public API contract tests

Cover `/health`, `/generate`, `/validate-gir`, `/render/svg` and `/render/tikz` with stable response/status expectations.

### PR 4 — Expand text-to-GIR benchmark suite

Add success, ambiguity and unsupported cases so text-to-GIR behavior is a product contract.

### PR 5 — Expand rule-based adapter without LLM

Support triangle, midpoint and specified angle bisector while keeping ambiguous/unsupported cases explicit.

### PR 6 — Add render benchmark layer

Add `gir_to_svg` and `gir_to_tikz` benchmark suites with structural output checks.

### PR 7 — Canonical MVP layout

Support arbitrary labels, midpoint, median and altitude layout through canonical single-triangle strategy.

### PR 8 — MVP roadmap rewrite

Align documentation with the actual MVP path and lock scope against solver/frontend/LLM creep.

### PR 9 — Verification hardening

Make local and CI gates stricter so the MVP release checklist is enforceable.

### PR 10 — Optional strictacode audit

Add optional architecture-health audit without making it a runtime dependency or MVP blocker.

## 15. Release Checklist

Before tagging MVP:

- [ ] All verification commands pass.
- [ ] CI is green.
- [ ] Schema is fresh.
- [ ] Benchmarks pass with `failed == 0`.
- [ ] API contract tests pass.
- [ ] CLI smoke tests pass.
- [ ] README quickstart works.
- [ ] MVP non-goals are documented.
- [ ] Known limitations are documented.
- [ ] No hidden LLM dependency exists.
- [ ] No renderer bypasses semantic validation.

## 16. Risks and Non-Goals

### Risks

- Scope creep into LLM, frontend, solver or platform work before the compiler loop is stable.
- Benchmarks that are too weak to detect regressions.
- Layout becoming a hidden solver.
- Renderers starting to fix invalid geometry.
- API domain errors mixing with HTTP protocol errors.
- Documentation promising more than the code verifies.

### Mitigation

- Keep the StrictTail protocol active.
- Add or update benchmarks before implementing feature behavior.
- Keep public render validation gates.
- Keep AI adapter deterministic until MVP.
- Treat unsupported inputs as explicit `error` or `needs_clarification`, never silent success.
- Keep post-MVP features out of MVP acceptance criteria.

## 17. Post-MVP Direction

Post-MVP work may include:

- real LLM adapter behind strict draft-GIR contract;
- more geometry constructions;
- richer layout engine;
- visual regression testing;
- frontend preview;
- PDF export;
- sketch input;
- optional solver;
- multi-user persistence and collaboration.

These must be added only after the MVP compiler loop is stable, benchmarked, validated and documented.
