import json
from dataclasses import replace

import pytest

from crosstheme.engine import SIZES, Candidate, Puzzle, construct, normalize, validate
from crosstheme.seeds import starter_candidates


@pytest.mark.parametrize("topic", ["Software engineering", "Roman history"])
@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
@pytest.mark.parametrize("size", SIZES)
def test_generated_grids_are_valid(topic, difficulty, size):
    _, candidates = starter_candidates(topic, difficulty)
    p = construct(candidates, topic=topic, difficulty=difficulty, size=size, seed=42)
    validate(p)
    assert len(p.entries) == SIZES[size][0]
    assert p.width <= SIZES[size][1] and p.height <= SIZES[size][1]
    assert {e.direction for e in p.entries} == {"across", "down"}
    # Every run of adjacent letters must correspond to exactly one supplied clue.
    solution = p.solution
    for direction, (dr, dc) in {"across": (0, 1), "down": (1, 0)}.items():
        for r, c in solution:
            if (r - dr, c - dc) in solution or (r + dr, c + dc) not in solution:
                continue
            letters = ""
            rr, cc = r, c
            while (rr, cc) in solution:
                letters += solution[rr, cc]
                rr, cc = rr + dr, cc + dc
            assert any(
                e.row == r and e.col == c and e.direction == direction and e.answer == letters
                for e in p.entries
            )


def test_deterministic_and_portable(puzzle):
    _, candidates = starter_candidates("software", "medium")
    again = construct(candidates, topic="Software engineering", size="quick", seed=7)
    assert again.entries == puzzle.entries
    assert Puzzle.from_dict(json.loads(json.dumps(puzzle.to_dict()))) == puzzle


@pytest.mark.parametrize("seed", range(8))
def test_varied_seed_construction(seed):
    _, candidates = starter_candidates("Roman history", "hard")
    validate(construct(candidates, topic="Rome", size="long", seed=seed))


def test_reject_invalid_candidates():
    with pytest.raises(ValueError, match="at least"):
        construct([Candidate("ab", "Too short"), Candidate("ANY", "")], topic="Test")
    with pytest.raises(ValueError, match="Only"):
        construct([Candidate(ch * 3, "A clue") for ch in "ABCDEFGH"], topic="Test", size="quick")


def test_validator_rejects_bad_crossings_numbering_and_version(puzzle):
    first = puzzle.entries[0]
    with pytest.raises(ValueError, match="numbering"):
        validate(replace(puzzle, entries=(replace(first, number=99), *puzzle.entries[1:])))
    with pytest.raises(ValueError):
        validate(replace(puzzle, entries=(replace(first, row=99), *puzzle.entries[1:])))
    with pytest.raises(ValueError, match="version"):
        Puzzle.from_dict({**puzzle.to_dict(), "version": 2})
    assert normalize("Café-au-lait") == "CAFEAULAIT"
