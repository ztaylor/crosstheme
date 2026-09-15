# Crosstheme working agreement

Own the complete implementation and verification loop. Make reasonable reversible decisions;
ask only for missing product decisions that materially change scope. Keep the final handoff
concise: behavior delivered, verification, concrete remaining limitations.

## Boundaries

- `engine.py` and `session.py` stay standard-library-only and independent of Textual, SQLite,
  subprocesses, and network access. Clients must be replaceable.
- Providers supply candidate content; Python constructs and independently validates grids.
- Never execute model output. Invoke CLI providers with argument arrays and stdin, no shell.
- Keep puzzle definitions immutable. Save progress transactionally, preserve completed times,
  and count active play only. Version storage and serialized contracts before breaking changes.
- Theme-first freeform grids are deliberate. Do not claim strict NYT grid construction.
- No hidden correctness feedback before completion; checks/reveals are explicit assistance.
- Grid highlights must cover shared borders and junctions consistently. Test full cell bounds,
  including crossings, with error > cursor > selected-answer color precedence.
- Keep every alphabet key available during play. Textual's command palette is disabled so
  Ctrl+P belongs to pencil mode. Gameplay letters and shortcuts share the grid widget queue;
  priority app shortcuts can overtake queued letters. Test rapid type/navigation/quit batches.

## Commands and evidence

- Install: `uv sync --locked`
- Run: `uv run crosstheme`
- Lint: `uv run ruff check src tests`
- Format: `uv run ruff format --check src tests`
- Tests: `uv run pytest -q`
- Package: `uv build`

Use deterministic clocks/seeds for domain tests and Textual `run_test` for UI behavior.
Test meaningful failure boundaries, persistence, and workflows rather than mirroring code.
Test at 80x24 and a larger terminal for UI changes. Real provider smoke tests use the user's
existing CLI login and quota; never put credentials, databases, or private prompts in Git.
`uv.lock` is generated; update it through uv. SVGs in docs are generated visual snapshots.
