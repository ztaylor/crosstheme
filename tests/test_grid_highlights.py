"""Selection must cover complete cells, even where other answers meet their borders."""

import pytest
from rich.console import Console

from crosstheme.app import CrosswordGrid
from crosstheme.engine import Progress
from crosstheme.session import Session


@pytest.mark.parametrize("height", [2, 3])
def test_selected_answer_has_uniform_background_through_crossings(puzzle, height):
    session = Session(puzzle, Progress())
    grid = CrosswordGrid(session)
    grid.cell_height = height
    console = Console()
    for entry in puzzle.entries:
        session.select_entry(entry)
        rendered = grid.render()
        rows = rendered.split("\n")
        cursor_r, cursor_c = session.progress.cursor
        cursor_box = (
            cursor_c * 6,
            cursor_r * height,
            cursor_c * 6 + 6,
            cursor_r * height + height,
        )
        for r, c in entry.cells:
            # Include all four borders and junctions, not just the five interior columns.
            for y in range(r * height, (r + 1) * height + 1):
                for x in range(c * 6, (c + 1) * 6 + 1):
                    in_cursor = (
                        cursor_box[0] <= x <= cursor_box[2] and cursor_box[1] <= y <= cursor_box[3]
                    )
                    expected = "#e3b875" if in_cursor else "#b5c9af"
                    assert rows[y].get_style_at_offset(console, x).bgcolor.name == expected


@pytest.mark.parametrize("height", [2, 3])
def test_error_background_covers_borders_and_overrides_selection(puzzle, height):
    session = Session(puzzle, Progress())
    grid = CrosswordGrid(session)
    grid.cell_height = height
    # A crossing previously got a different border color from its neighboring answer.
    crossing = next(
        cell
        for cell in puzzle.solution
        if sum(cell in entry.cells for entry in puzzle.entries) == 2
    )
    session.select_cell(crossing)
    grid.errors.add(crossing)
    rows = grid.render().split("\n")
    console = Console()
    r, c = crossing
    for y in range(r * height, (r + 1) * height + 1):
        for x in range(c * 6, (c + 1) * 6 + 1):
            assert rows[y].get_style_at_offset(console, x).bgcolor.name == "#c46858"
