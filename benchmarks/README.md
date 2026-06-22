# Benchmarks

Benchmarks are product contracts for GeometryOS. They define what the current
MVP understands, what needs clarification, and what must fail explicitly instead
of producing hallucinated GIR.

## text_to_gir

Each text-to-GIR benchmark case contains an input file and one expected file:

- `<name>.input.txt` — user-facing geometry prompt.
- `<name>.expected.gir.json` — success case; must parse as `GirScene` and pass semantic validation.
- `<name>.expected.json` — non-success case; used for `needs_clarification` or `error` statuses.

Supported statuses:

- `success` — adapter returns draft GIR that passes Pydantic and semantic validation.
- `needs_clarification` — adapter returns structured ambiguities and no GIR.
- `error` — adapter explicitly rejects unsupported or malformed input and returns no GIR.

Current MVP success coverage is intentionally small and deterministic: triangle
ABC, altitude from A to BC, median from A to BC, midpoint M of BC, and angle
bisector of angle A. Other school-geometry constructions are tracked as explicit
`error` cases until their adapter support is implemented in later PRs.

Run benchmarks with:

```bash
uv run python scripts/run_benchmarks.py
uv run gir benchmark --root .
```

Passing benchmarks means current behavior matches the product contract; it does
not mean every listed construction is supported yet.

## gir_to_svg

Render benchmarks verify that valid GIR scenes can be rendered through the public
SVG renderer entrypoint. They use structural output checks, not pixel-perfect
visual snapshots.

Each case contains:

- `<name>.gir.json` — semantically valid render input.
- `<name>.expected.json` — structural expectations for the rendered artifact.

Expected JSON supports:

- `must_contain`
- `must_not_contain`
- `min_occurrences`

## gir_to_tikz

TikZ render benchmarks use the same format as `gir_to_svg`, but validate the
public TikZ renderer output. Current render benchmark coverage intentionally
stays within MVP layout labels `A`, `B`, `C`, `H`, and `M`.
