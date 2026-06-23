# Benchmark Contract

## Purpose

Benchmarks are product contracts for GeometryOS MVP behavior. They define which
inputs must succeed, which inputs need clarification, which inputs must fail
explicitly, and which validated GIR scenes must render structurally valid SVG and
TikZ output.

## Suites

Current benchmark suites:

- `benchmarks/text_to_gir` — text prompt → adapter result / draft GIR.
- `benchmarks/gir_to_svg` — semantic-valid GIR → SVG structural checks.
- `benchmarks/gir_to_tikz` — semantic-valid GIR → TikZ structural checks.

## Input

Text-to-GIR cases contain:

- `<name>.input.txt`;
- `<name>.expected.gir.json` for `success` cases;
- `<name>.expected.json` for `needs_clarification` or `error` cases.

Render cases contain:

- `<name>.gir.json`;
- `<name>.expected.json` with structural output expectations.

## Output

The shared benchmark runner returns a JSON-compatible summary with:

- `total`;
- `passed`;
- `failed`;
- `failures`;
- `suites` with per-suite counts.

A green MVP benchmark run has `failed == 0`.

## Invariants

- GIR is the source of truth.
- Benchmarks must not require LLM output.
- Success `.expected.gir.json` files must parse as `GirScene` and pass semantic validation.
- Non-success text cases must use `status: "needs_clarification"` or `status: "error"`.
- Render benchmarks call public render entrypoints and do not bypass validation.
- Render expectations are structural, not pixel-perfect snapshots.

## Failure modes

- Adapter returns the wrong domain status.
- Adapter misses expected object ids, constraint ids/types or construction actions.
- Expected ambiguity codes are missing.
- Expected GIR does not parse or fails semantic validation.
- Render output misses required substrings, includes forbidden substrings or has too few draw commands.

## Minimal JSON examples

Non-success text case:

```json
{"status":"needs_clarification","ambiguities":[{"code":"missing_angle"}]}
```

Render expectation:

```json
{"type":"svg","must_contain":["<svg","A"],"must_not_contain":["Traceback"],"min_occurrences":{"<line":3}}
```
