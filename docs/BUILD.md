# Development notes

Crosstheme is a small terminal app with a portable Python domain layer. The repository
contains the app, offline clue sets, tests, and generated screenshots.

## Design

- `engine.py` constructs and independently validates connected, theme-first grids. Puzzle
  definitions are immutable; the engine and session modules use only the standard library.
- `session.py` handles navigation, editing, assistance, and active play time. Its injectable
  clock keeps timing tests deterministic.
- `providers.py` gets candidate answers and clues from local CLI providers or offline content.
  Python constructs the grid. Provider output is parsed as data and never executed.
- `storage.py` saves progress transactionally in SQLite, with versioned storage and puzzle JSON.
- `app.py` and `app.tcss` provide the Textual interface; `cli.py` wires up terminal commands.

Grid sizes target 8, 14, or 20 entries. These freeform crosswords prioritize thematic answers;
rotational symmetry and two answers through every letter are not construction requirements.

## Verification

```sh
uv sync --locked
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest -q
uv build
```

The tests run offline with temporary databases and fake provider executables. They cover:

- Both starter themes, every difficulty and length, seeded construction, independent grid
  invariants, JSON round-trips, and invalid geometry or candidate pools.
- Pause/resume, completion, assistance, save/reopen, and simultaneous library initialization.
- Provider response parsing, subprocess arguments and stdin, timeouts, and cancellation.
- Textual play and navigation at 80 × 24 and larger terminal sizes, generation and cancellation,
  complete cell highlights, mouse targets, and rapid letter/navigation/quit batches.

GitHub Actions runs the same checks on pushes and pull requests. Real provider checks are manual
and use the caller's existing CLI authentication and quota; they are not part of CI.

## Screenshots

The SVGs are generated Textual snapshots using offline Roman-history puzzles and sample progress:

- [Playing](play.svg)
- [Puzzle shelf](shelf.svg)
- [Compact terminal](compact.svg)

Regenerate screenshots from the app when changing the interface; do not hand-edit the SVGs.
Use a temporary library with sample data for captures.

## Scope and limitations

Model-generated clues are structurally filtered but are not independently fact-checked or
professionally edited. Use one solving app per library to avoid concurrent progress overwrites.
Linux and macOS are the intended terminal environments; a native Omarchy/Wayland session has
not been manually verified. There is no bundled web/mobile client or interactive import UI.

Keep credentials, personal puzzle libraries, exports, and private prompts out of commits.
