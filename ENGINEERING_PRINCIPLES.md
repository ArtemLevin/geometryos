# Engineering Principles

- Single Source of Truth: GIR, not LLM output or renderer coordinates.
- Context Boundary: each layer has explicit inputs and outputs.
- Immutable GIR: normalized GIR changes must be explicit.
- Agent Isolation: AI adapters cannot render or validate by assertion.
- Event First later: domain events can be added after the MVP stabilizes.
- Rule of Three: avoid premature abstractions until repeated need appears.
- Plugin First later: renderers and adapters can become plugins later.
- Human-in-the-loop: ambiguity must be surfaced.
- Observability: validation reports and benchmark summaries are first-class.
