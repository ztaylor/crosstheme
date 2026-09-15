"""UI-independent play session. Inject a monotonic clock for deterministic tests."""

from __future__ import annotations

import time
from collections.abc import Callable

from crosstheme.engine import Entry, Progress, Puzzle, now


class Session:
    def __init__(
        self, puzzle: Puzzle, progress: Progress, clock: Callable[[], float] = time.monotonic
    ):
        self.puzzle, self.progress, self.clock = puzzle, progress, clock
        self.running = not bool(progress.completed_at)
        self.last_tick = clock()
        if progress.cursor not in puzzle.solution:
            progress.cursor = puzzle.entries[0].cells[0]
        self.select_cell(progress.cursor)

    @property
    def entry(self) -> Entry:
        matching = [e for e in self.puzzle.entries if self.progress.cursor in e.cells]
        return next((e for e in matching if e.direction == self.progress.direction), matching[0])

    def tick(self) -> None:
        current = self.clock()
        if self.running and not self.progress.completed_at:
            self.progress.elapsed += max(0, current - self.last_tick)
        self.last_tick = current

    def pause(self) -> None:
        self.tick()
        self.running = False

    def resume(self) -> None:
        self.last_tick = self.clock()
        self.running = not bool(self.progress.completed_at)

    def select_cell(self, cell: tuple[int, int]) -> None:
        if cell in self.puzzle.solution:
            self.progress.cursor = cell
            self.progress.direction = self.entry.direction

    def select_entry(self, entry: Entry) -> None:
        self.progress.cursor = entry.cells[0]
        self.progress.direction = entry.direction

    def toggle_direction(self) -> None:
        self.progress.direction = "down" if self.progress.direction == "across" else "across"
        self.progress.direction = self.entry.direction

    def next_entry(self, delta: int = 1) -> None:
        ordered = sorted(self.puzzle.entries, key=lambda e: (e.direction, e.number))
        self.select_entry(ordered[(ordered.index(self.entry) + delta) % len(ordered)])

    def move(self, dr: int, dc: int) -> None:
        direction = "down" if dr else "across"
        if self.progress.direction != direction and any(
            e.direction == direction and self.progress.cursor in e.cells
            for e in self.puzzle.entries
        ):
            self.progress.direction = direction
            return
        r, c = self.progress.cursor
        while 0 <= r + dr < self.puzzle.height and 0 <= c + dc < self.puzzle.width:
            r, c = r + dr, c + dc
            if (r, c) in self.puzzle.solution:
                self.select_cell((r, c))
                return

    def finish_if_correct(self) -> bool:
        self.tick()
        if not self.progress.completed_at and self.progress.is_correct(self.puzzle):
            self.progress.completed_at = now()
            self.running = False
            return True
        return False

    def type_letter(self, letter: str, pencil: bool = False) -> bool:
        if not self.running:
            return False
        entry = self.entry
        index = entry.cells.index(self.progress.cursor)
        self.progress.put(self.puzzle, self.progress.cursor, letter, pencil)
        completed = self.finish_if_correct()
        if index + 1 < len(entry.cells):
            self.progress.cursor = entry.cells[index + 1]
        return completed

    def erase(self, back: bool = True) -> None:
        if not self.running:
            return
        key = self.progress.cell_key(self.progress.cursor)
        if back and not self.progress.letters.get(key):
            cells = self.entry.cells
            self.progress.cursor = cells[max(0, cells.index(self.progress.cursor) - 1)]
        self.progress.put(self.puzzle, self.progress.cursor, "")
