import asyncio

import pytest
from textual.widgets import Input, Select

from crosstheme.app import CrossthemeApp, LibraryScreen, MessageDialog, NewPuzzleScreen, PlayScreen
from crosstheme.engine import Progress
from crosstheme.storage import Store


@pytest.mark.parametrize("dimensions", [(120, 45), (80, 24)])
async def test_play_pause_help_resume_and_quit(tmp_path, puzzle, dimensions):
    store = Store(tmp_path / "puzzles.db")
    store.save(puzzle, Progress())
    app = CrossthemeApp(store, puzzle.id)
    async with app.run_test(size=dimensions) as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, PlayScreen)
        first_cell = screen.session.progress.cursor
        await pilot.press("q", "h")
        assert screen.session.progress.letters[Progress.cell_key(first_cell)] == "Q"
        await pilot.press("ctrl+p", "a")
        assert screen.session.progress.pencil
        await pilot.press("f2")
        assert screen.paused and not screen.session.running
        letters = screen.session.progress.letters.copy()
        await pilot.press("z")
        assert screen.session.progress.letters == letters
        await pilot.press("f2", "f1")
        assert isinstance(app.screen, MessageDialog)
        assert not screen.session.running
        await pilot.press("escape")
        assert screen.session.running
        await pilot.press("tab", "space")
        saved_cursor = screen.session.progress.cursor
        await pilot.press("escape")
        assert isinstance(app.screen, LibraryScreen)
        _, saved = store.load(puzzle.id)
        assert saved.letters == screen.session.progress.letters
        assert saved.cursor == saved_cursor
        app.play(puzzle.id)
        await pilot.pause()
        assert app.screen.session.progress.cursor == saved_cursor
        await pilot.press("ctrl+q")
    store.close()


async def test_reveal_confirmation_and_completion(tmp_path, puzzle):
    store = Store(tmp_path / "puzzles.db")
    progress = Progress()
    for cell, letter in puzzle.solution.items():
        progress.put(puzzle, cell, letter)
    missing = puzzle.entries[0].cells[0]
    progress.letters.pop(progress.cell_key(missing))
    progress.cursor = missing
    store.save(puzzle, progress)
    app = CrossthemeApp(store, puzzle.id)
    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause()
        screen = app.screen
        await pilot.press("ctrl+r")
        assert isinstance(app.screen, MessageDialog)
        await pilot.press("escape")
        assert not screen.session.progress.revealed
        await pilot.press("ctrl+r")
        await pilot.click("#accept")
        await pilot.pause()
        assert screen.session.progress.completed_at
        assert isinstance(app.screen, MessageDialog)
        _, saved = store.load(puzzle.id)
        assert saved.completed_at and saved.revealed
        elapsed = saved.elapsed
        await pilot.press("escape", "z")
        assert screen.session.progress.elapsed == elapsed
    store.close()


async def test_create_from_empty_shelf(tmp_path):
    store = Store(tmp_path / "puzzles.db")
    app = CrossthemeApp(store)
    async with app.run_test(size=(100, 45)) as pilot:
        await pilot.pause()
        await pilot.click("#starter-software")
        assert isinstance(app.screen, NewPuzzleScreen)
        app.screen.query_one("#size", Select).value = "quick"
        await pilot.click("#generate")
        for _ in range(100):
            await pilot.pause(0.05)
            if isinstance(app.screen, PlayScreen):
                break
        assert isinstance(app.screen, PlayScreen)
        assert len(store.list()) == 1
        await pilot.press("escape")
        app.screen.query_one("#filter", Input).value = "no such topic"
        await pilot.pause()
        assert not app.screen.query("PuzzleCard")
    store.close()


async def test_cancel_generation_leaves_no_partial_puzzle(tmp_path, monkeypatch):
    stopped = asyncio.Event()

    async def slow_generate(*args, **kwargs):
        try:
            await asyncio.sleep(30)
        finally:
            stopped.set()

    monkeypatch.setattr("crosstheme.app.generate", slow_generate)
    store = Store(tmp_path / "puzzles.db")
    app = CrossthemeApp(store)
    async with app.run_test(size=(100, 45)) as pilot:
        await pilot.pause()
        await pilot.click("#starter-software")
        await pilot.click("#generate")
        await pilot.pause()
        await pilot.press("escape")
        await asyncio.wait_for(stopped.wait(), 2)
        assert isinstance(app.screen, LibraryScreen)
        assert store.list() == []
    store.close()


async def test_quit_drains_buffered_letters(tmp_path, puzzle):
    from textual import events

    store = Store(tmp_path / "puzzles.db")
    store.save(puzzle, Progress())
    app = CrossthemeApp(store, puzzle.id)
    async with app.run_test() as pilot:
        await pilot.pause()
        cell = app.screen.session.progress.cursor
        # Real terminals can deliver the final letter and quit shortcut in one input batch.
        app.post_message(events.Key("q", "q"))
        app.post_message(events.Key("ctrl+q", None))
        await pilot.pause()
    assert store.load(puzzle.id)[1].letters[Progress.cell_key(cell)] == "Q"
    store.close()


async def test_buffered_navigation_keeps_letters_in_the_right_words(tmp_path, puzzle):
    from textual import events

    store = Store(tmp_path / "puzzles.db")
    store.save(puzzle, Progress())
    app = CrossthemeApp(store, puzzle.id)
    async with app.run_test() as pilot:
        await pilot.pause()
        session = app.screen.session
        first = session.progress.cursor
        ordered = sorted(puzzle.entries, key=lambda e: (e.direction, e.number))
        second = ordered[(ordered.index(session.entry) + 1) % len(ordered)].cells[0]
        for key, char in [("q", "q"), ("tab", None), ("h", "h")]:
            app.post_message(events.Key(key, char))
        await pilot.pause()
        assert session.progress.letters[Progress.cell_key(first)] == "Q"
        assert session.progress.letters[Progress.cell_key(second)] == "H"
    store.close()


@pytest.mark.parametrize("dimensions", [(150, 45), (80, 24)])
async def test_grid_mouse_targets_after_resize_and_scroll(tmp_path, puzzle, dimensions):
    from crosstheme.app import CrosswordGrid

    store = Store(tmp_path / "puzzles.db")
    store.save(puzzle, Progress())
    app = CrossthemeApp(store, puzzle.id)
    async with app.run_test(size=dimensions) as pilot:
        await pilot.pause()
        screen = app.screen
        grid = screen.query_one(CrosswordGrid)
        # Follow a square at the far edge, including compact terminals that must scroll.
        target = max(puzzle.solution)
        screen.session.select_cell(target)
        screen.refresh_play()
        await pilot.pause()
        r, c = target
        click_offset = (c * grid.cell_width + 3, r * grid.cell_height + 1)
        before = screen.session.progress.direction
        await pilot.click("#grid", offset=click_offset)
        assert screen.session.progress.cursor == target
        await pilot.press("x")
        assert screen.session.progress.letters[Progress.cell_key(target)] == "X"
        # Shared borders should not unexpectedly move or switch the active entry.
        screen.session.select_cell(target)
        screen.refresh_play()
        await pilot.pause()
        before = screen.session.progress.direction
        await pilot.click("#grid", offset=(c * grid.cell_width, r * grid.cell_height + 1))
        assert screen.session.progress.cursor == target
        assert screen.session.progress.direction == before
        # Every rendered row has a consistent width, including edges and blocked cells.
        rows = grid.render().plain.splitlines()
        assert {len(row) for row in rows} == {puzzle.width * grid.cell_width + 1}
        assert "·" not in grid.render().plain
    store.close()
