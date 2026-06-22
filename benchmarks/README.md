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

Current MVP success coverage is intentionally small: triangle, altitude, and
median prompts for triangle ABC. Other school-geometry constructions are tracked
as explicit `error` cases until their adapter support is implemented in later PRs.

Run benchmarks with:

```bash
uv run python scripts/run_benchmarks.py
uv run gir benchmark --root .
```

Passing benchmarks means current behavior matches the product contract; it does
not mean every listed construction is supported yet.
