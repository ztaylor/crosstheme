from dataclasses import asdict

import pytest

from crosstheme.engine import Progress
from crosstheme.session import Session
from crosstheme.storage import Store


def test_clock_pause_resume_complete_and_revisit(puzzle):
    clock = [100.0]
    state = Progress()
    session = Session(puzzle, state, lambda: clock[0])
    clock[0] += 17
    session.pause()
    assert state.elapsed == 17
    clock[0] += 1000
    session.resume()
    clock[0] += 13
    for cell, letter in puzzle.solution.items():
        state.put(puzzle, cell, letter)
    assert session.finish_if_correct()
    assert state.elapsed == 30 and state.completed_at
    completed_at = state.completed_at
    clock[0] += 500
    session.resume()
    session.tick()
    assert state.elapsed == 30
    assert state.completed_at == completed_at
    before = state.letters.copy()
    session.type_letter("Z")
    assert state.letters == before


def test_save_resume_all_state_and_immutable_puzzle(tmp_path, puzzle):
    state = Progress(elapsed=123.4, cursor=puzzle.entries[0].cells[0], direction="down")
    cells = list(puzzle.solution)
    state.put(puzzle, cells[0], "Q", pencil=True)
    state.reveal(puzzle, [cells[1]])
    state.check(puzzle, cells)
    store = Store(tmp_path / "nested" / "library.db")
    store.save(puzzle, state)
    store.close()
    reopened = Store(tmp_path / "nested" / "library.db")
    loaded, progress = reopened.load(puzzle.id)
    assert loaded == puzzle
    assert asdict(progress) == asdict(state)
    assert len(reopened.list()) == 1
    reopened.close()


def test_crossing_single_state_and_checks_do_not_reveal(puzzle):
    state = Progress()
    crossing = next(c for c in puzzle.solution if sum(c in e.cells for e in puzzle.entries) == 2)
    state.put(puzzle, crossing, "Z" if puzzle.solution[crossing] != "Z" else "X")
    before = state.letters.copy()
    assert state.check(puzzle, [crossing]) == {crossing}
    assert state.letters == before
    state.reveal(puzzle, [crossing])
    assert state.letters[state.cell_key(crossing)] == puzzle.solution[crossing]
    state.put(puzzle, crossing, "Q")
    assert state.letters[state.cell_key(crossing)] == puzzle.solution[crossing]
    assert state.revealed == [state.cell_key(crossing)]
    with pytest.raises(ValueError):
        state.put(puzzle, crossing, "AB")


def test_navigation_and_backspace(puzzle):
    state = Progress()
    session = Session(puzzle, state)
    entry = session.entry
    session.type_letter("q")
    assert state.letters[state.cell_key(entry.cells[0])] == "Q"
    assert state.cursor == entry.cells[1]
    session.erase()
    assert state.cursor == entry.cells[0]
    assert not state.letters[state.cell_key(entry.cells[0])]
    session.next_entry()
    assert session.entry != entry
    session.next_entry(-1)
    assert session.entry == entry


def test_simultaneous_library_initialization(tmp_path, puzzle):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(6)
    path = tmp_path / "shared.db"

    def open_and_save(index):
        from dataclasses import replace

        barrier.wait()
        store = Store(path)
        store.save(replace(puzzle, id=f"test-{index}"), Progress())
        store.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(open_and_save, range(6)))
    store = Store(path)
    assert len(store.list()) == 6
    store.close()
