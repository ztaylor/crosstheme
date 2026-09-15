"""Versioned SQLite persistence; each save is an atomic transaction."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path

from crosstheme.engine import Progress, Puzzle, now


def default_path() -> Path:
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return Path(os.environ.get("CROSSTHEME_DATA_DIR", root / "crosstheme")) / "puzzles.sqlite3"


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10)
        # WAL's first-time transition can return SQLITE_BUSY immediately even with a busy timeout.
        for attempt in range(20):
            try:
                self.db.execute("PRAGMA journal_mode=WAL")
                break
            except sqlite3.OperationalError as error:
                if "locked" not in str(error) or attempt == 19:
                    self.db.close()
                    raise
                time.sleep(0.05)
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            self.db.close()
            raise ValueError("This library needs a newer version of Crosstheme")
        with self.db:
            self.db.execute("""CREATE TABLE IF NOT EXISTS puzzles (
                id TEXT PRIMARY KEY, puzzle TEXT NOT NULL, progress TEXT NOT NULL,
                updated_at TEXT NOT NULL)""")
            self.db.execute("PRAGMA user_version=1")

    def save(self, puzzle: Puzzle, progress: Progress) -> None:
        with self.db:
            self.db.execute(
                """INSERT INTO puzzles VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET progress=excluded.progress,
                updated_at=excluded.updated_at""",
                (puzzle.id, json.dumps(puzzle.to_dict()), json.dumps(asdict(progress)), now()),
            )

    def load(self, puzzle_id: str) -> tuple[Puzzle, Progress]:
        row = self.db.execute(
            "SELECT puzzle, progress FROM puzzles WHERE id=?", (puzzle_id,)
        ).fetchone()
        if row is None:
            raise KeyError(puzzle_id)
        data = json.loads(row[1])
        data["cursor"] = tuple(data["cursor"])
        return Puzzle.from_dict(json.loads(row[0])), Progress(**data)

    def list(self) -> list[tuple[Puzzle, Progress]]:
        ids = self.db.execute("SELECT id FROM puzzles ORDER BY updated_at DESC").fetchall()
        return [self.load(row[0]) for row in ids]

    def close(self) -> None:
        self.db.close()
