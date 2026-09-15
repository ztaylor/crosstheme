"""Pure domain layer: no UI, database, subprocesses, or network dependencies."""

from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

Direction = Literal["across", "down"]
DIFFICULTIES = ("easy", "medium", "hard")
SIZES = {"quick": (8, 13), "standard": (14, 17), "long": (20, 21)}


def now() -> str:
    return datetime.now(UTC).isoformat()


def normalize(answer: str) -> str:
    text = unicodedata.normalize("NFKD", answer).encode("ascii", "ignore").decode()
    return re.sub("[^A-Z]", "", text.upper())


@dataclass(frozen=True)
class Candidate:
    answer: str
    clue: str
    explanation: str = ""


@dataclass(frozen=True)
class Entry:
    number: int
    row: int
    col: int
    direction: Direction
    answer: str
    clue: str
    explanation: str = ""

    @property
    def key(self) -> str:
        return f"{self.number}{self.direction[0].upper()}"

    @property
    def cells(self) -> list[tuple[int, int]]:
        return [
            (
                self.row + (i if self.direction == "down" else 0),
                self.col + (i if self.direction == "across" else 0),
            )
            for i in range(len(self.answer))
        ]


@dataclass(frozen=True)
class Puzzle:
    id: str
    title: str
    topic: str
    difficulty: str
    size: str
    provider: str
    created_at: str
    width: int
    height: int
    entries: tuple[Entry, ...]
    seed: int
    version: int = 1

    @property
    def solution(self) -> dict[tuple[int, int], str]:
        return {
            cell: letter
            for e in self.entries
            for cell, letter in zip(e.cells, e.answer, strict=True)
        }

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Puzzle:
        if data.get("version") != 1:
            raise ValueError("Unsupported puzzle version")
        puzzle = cls(**{**data, "entries": tuple(Entry(**e) for e in data["entries"])})
        validate(puzzle)
        return puzzle


def validate(puzzle: Puzzle) -> None:
    """Check geometry independently, including unintended adjacent words."""
    if puzzle.difficulty not in DIFFICULTIES or puzzle.size not in SIZES:
        raise ValueError("Unknown difficulty or size")
    if not (1 <= puzzle.width <= 25 and 1 <= puzzle.height <= 25):
        raise ValueError("Invalid grid dimensions")
    if len(puzzle.entries) < 2:
        raise ValueError("A crossword needs at least two entries")
    owners: dict[tuple[int, int], list[Entry]] = {}
    letters: dict[tuple[int, int], str] = {}
    answers = set()
    starts = sorted({(e.row, e.col) for e in puzzle.entries})
    for e in puzzle.entries:
        if e.direction not in ("across", "down") or not re.fullmatch("[A-Z]{3,21}", e.answer):
            raise ValueError("Invalid entry")
        if not e.clue.strip() or e.answer in answers:
            raise ValueError("Missing clue or duplicate answer")
        answers.add(e.answer)
        if e.number != starts.index((e.row, e.col)) + 1:
            raise ValueError("Incorrect clue numbering")
        for cell, letter in zip(e.cells, e.answer, strict=True):
            r, c = cell
            if not (0 <= r < puzzle.height and 0 <= c < puzzle.width):
                raise ValueError("Entry outside grid")
            if cell in letters and letters[cell] != letter:
                raise ValueError("Mismatched crossing")
            if any(other.direction == e.direction for other in owners.get(cell, [])):
                raise ValueError("Overlapping entries")
            owners.setdefault(cell, []).append(e)
            letters[cell] = letter
    for (r, c), entries in owners.items():
        for neighbor, direction in (((r, c + 1), "across"), ((r + 1, c), "down")):
            if neighbor in owners and not any(
                e.direction == direction and e in owners[neighbor] for e in entries
            ):
                raise ValueError("Unclued adjacent letters")
    seen = {puzzle.entries[0].key}
    while True:
        expanded = seen | {
            e.key for es in owners.values() if any(x.key in seen for x in es) for e in es
        }
        if expanded == seen:
            break
        seen = expanded
    if len(seen) != len(puzzle.entries):
        raise ValueError("Disconnected grid")


def construct(
    candidates: list[Candidate],
    *,
    topic: str,
    difficulty: str = "medium",
    size: str = "standard",
    provider: str = "offline",
    title: str = "",
    seed: int | None = None,
) -> Puzzle:
    if difficulty not in DIFFICULTIES or size not in SIZES:
        raise ValueError("Unknown difficulty or size")
    target, limit = SIZES[size]
    pool: dict[str, Candidate] = {}
    for item in candidates:
        answer = normalize(item.answer)
        if 3 <= len(answer) <= min(15, limit) and item.clue.strip():
            pool.setdefault(answer, Candidate(answer, item.clue.strip(), item.explanation))
    if len(pool) < target:
        raise ValueError(f"Need at least {target} distinct usable answers; received {len(pool)}")
    seed = seed if seed is not None else random.SystemRandom().randrange(2**32)
    rng = random.Random(seed)
    best: list[Entry] = []
    best_score = float("-inf")
    for attempt in range(65):
        words = list(pool.values())
        rng.shuffle(words)
        first = words.pop(0)
        placed = [Entry(0, 0, 0, "across", first.answer, first.clue, first.explanation)]
        grid = {
            cell: (ch, {"across"}) for cell, ch in zip(placed[0].cells, first.answer, strict=True)
        }
        while words and len(placed) < target:
            options = []
            for word in words:
                for i, ch in enumerate(word.answer):
                    for (r, c), (existing, directions) in list(grid.items()):
                        if existing != ch or len(directions) != 1:
                            continue
                        direction = "down" if "across" in directions else "across"
                        dr, dc = (1, 0) if direction == "down" else (0, 1)
                        row, col = r - dr * i, c - dc * i
                        cells = [(row + dr * j, col + dc * j) for j in range(len(word.answer))]
                        before = (row - dr, col - dc)
                        after = (row + dr * len(word.answer), col + dc * len(word.answer))
                        if before in grid or after in grid:
                            continue
                        crosses = 0
                        valid = True
                        for cell, letter in zip(cells, word.answer, strict=True):
                            rr, cc = cell
                            if cell in grid:
                                old, dirs = grid[cell]
                                if old != letter or direction in dirs:
                                    valid = False
                                    break
                                crosses += 1
                            elif (rr + dc, cc + dr) in grid or (rr - dc, cc - dr) in grid:
                                valid = False
                                break
                        if not valid:
                            continue
                        all_cells = list(grid) + cells
                        height = max(x[0] for x in all_cells) - min(x[0] for x in all_cells) + 1
                        width = max(x[1] for x in all_cells) - min(x[1] for x in all_cells) + 1
                        if height > limit or width > limit:
                            continue
                        score = crosses * 14 - height * width * 0.06 + rng.random() * 5
                        options.append((score, word, row, col, direction, cells))
            if not options:
                break
            _, word, row, col, direction, cells = max(options, key=lambda x: x[0])
            placed.append(Entry(0, row, col, direction, word.answer, word.clue, word.explanation))
            for cell, letter in zip(cells, word.answer, strict=True):
                if cell in grid:
                    grid[cell][1].add(direction)
                else:
                    grid[cell] = (letter, {direction})
            words.remove(word)
        rs, cs = [x[0] for x in grid], [x[1] for x in grid]
        area = (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)
        crossings = sum(len(dirs) == 2 for _, dirs in grid.values())
        score = len(placed) * 1000 + crossings * 8 - area
        if score > best_score:
            best, best_score = placed, score
        if len(best) == target and attempt >= 12:
            break
    if len(best) < target:
        raise ValueError(
            f"Only {len(best)} of {target} answers fit. Try another generation or quick size."
        )
    min_r, min_c = min(e.row for e in best), min(e.col for e in best)
    starts = sorted({(e.row, e.col) for e in best})
    entries = tuple(
        sorted(
            (
                Entry(
                    starts.index((e.row, e.col)) + 1,
                    e.row - min_r,
                    e.col - min_c,
                    e.direction,
                    e.answer,
                    e.clue,
                    e.explanation,
                )
                for e in best
            ),
            key=lambda e: (e.number, e.direction),
        )
    )
    cells = [cell for e in entries for cell in e.cells]
    puzzle = Puzzle(
        str(uuid4()),
        title or topic,
        topic,
        difficulty,
        size,
        provider,
        now(),
        max(c for _, c in cells) + 1,
        max(r for r, _ in cells) + 1,
        entries,
        seed,
    )
    validate(puzzle)
    return puzzle


@dataclass
class Progress:
    letters: dict[str, str] = field(default_factory=dict)
    pencil: list[str] = field(default_factory=list)
    pencil_mode: bool = False
    revealed: list[str] = field(default_factory=list)
    elapsed: float = 0.0
    completed_at: str | None = None
    checks: int = 0
    cursor: tuple[int, int] = (0, 0)
    direction: Direction = "across"

    @staticmethod
    def cell_key(cell: tuple[int, int]) -> str:
        return f"{cell[0]},{cell[1]}"

    def put(self, puzzle: Puzzle, cell: tuple[int, int], letter: str, pencil: bool = False) -> None:
        if self.completed_at:
            return
        if cell not in puzzle.solution or (letter and not re.fullmatch("[A-Za-z]", letter)):
            raise ValueError("Enter a single letter in an open cell")
        key = self.cell_key(cell)
        if key in self.revealed:
            return
        self.letters[key] = letter.upper()
        if key in self.pencil:
            self.pencil.remove(key)
        if pencil and letter:
            self.pencil.append(key)

    def is_correct(self, puzzle: Puzzle) -> bool:
        return all(
            self.letters.get(self.cell_key(cell)) == ch for cell, ch in puzzle.solution.items()
        )

    def filled(self, puzzle: Puzzle) -> int:
        return sum(bool(self.letters.get(self.cell_key(cell))) for cell in puzzle.solution)

    def check(self, puzzle: Puzzle, cells: list[tuple[int, int]]) -> set[tuple[int, int]]:
        self.checks += 1
        solution = puzzle.solution
        return {
            cell
            for cell in cells
            if self.letters.get(self.cell_key(cell))
            and self.letters[self.cell_key(cell)] != solution[cell]
        }

    def reveal(self, puzzle: Puzzle, cells: list[tuple[int, int]]) -> None:
        if self.completed_at:
            return
        for cell in cells:
            key = self.cell_key(cell)
            self.letters[key] = puzzle.solution[cell]
            if key not in self.revealed:
                self.revealed.append(key)
            if key in self.pencil:
                self.pencil.remove(key)


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"
