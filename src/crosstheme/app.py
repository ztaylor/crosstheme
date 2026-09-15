"""Textual presentation adapter. Domain and persistence have no dependency on this module."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.geometry import Region
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, LoadingIndicator, Select, Static

from crosstheme.engine import Entry, Progress, Puzzle, format_time
from crosstheme.providers import available_providers, generate
from crosstheme.session import Session
from crosstheme.storage import Store


class MessageDialog(ModalScreen[bool]):
    BINDINGS = [("escape", "cancel", "Close")]

    def __init__(self, title: str, message: str, confirm: bool = False):
        super().__init__()
        self.heading, self.message, self.confirm = title, message, confirm

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(self.heading, classes="dialog-title", markup=False)
            yield Static(self.message, markup=False)
            with Horizontal(classes="dialog-actions"):
                yield Button(
                    "Continue" if self.confirm else "Back to puzzle", id="accept", variant="primary"
                )
                if self.confirm:
                    yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "accept")

    def action_cancel(self) -> None:
        self.dismiss(False)


class PuzzleCard(Button):
    def __init__(self, puzzle: Puzzle, progress: Progress):
        self.puzzle_id = puzzle.id
        total = len(puzzle.solution)
        done = progress.filled(puzzle)
        status = "SOLVED" if progress.completed_at else ("IN PROGRESS" if done else "READY TO PLAY")
        assists = " · assisted" if progress.checks or progress.revealed else ""
        label = Text()
        label.append(f"{puzzle.title}\n", style="bold #f1dec2")
        label.append(
            f"{puzzle.topic}  ·  {puzzle.difficulty.upper()}  ·  {len(puzzle.entries)} clues\n",
            style="#a6a8a2",
        )
        label.append(
            f"{status}  {done}/{total} squares  ·  {format_time(progress.elapsed)}{assists}",
            style="#9dbb8c" if progress.completed_at else "#d4aa73",
        )
        super().__init__(label, classes="puzzle-card")


class LibraryScreen(Screen):
    BINDINGS = [("n", "new", "New puzzle"), ("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(id="library"):
            yield Static("C R O S S T H E M E", id="wordmark")
            yield Static("Follow your curiosity. Fill in the squares.", classes="muted")
            with Horizontal(id="library-bar"):
                yield Static("YOUR PUZZLE SHELF", id="shelf-label")
                yield Button("＋ New puzzle", id="new", variant="primary")
            yield Input(placeholder="Filter by topic, title, or difficulty…", id="filter")
            yield Static("", id="library-stats", classes="muted")
            yield VerticalScroll(id="shelf")
            yield Static(
                "Every puzzle saved locally. Every return picks up where you left off.",
                id="library-note",
                classes="muted",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_shelf()

    def on_screen_resume(self) -> None:
        if self.is_mounted:
            self.refresh_shelf()

    @work(exclusive=True)
    async def refresh_shelf(self) -> None:
        shelf = self.query_one("#shelf", VerticalScroll)
        await shelf.remove_children()
        items = self.app.store.list()
        query = self.query_one("#filter", Input).value.casefold()
        visible = [
            (p, s) for p, s in items if query in f"{p.topic} {p.title} {p.difficulty}".casefold()
        ]
        solved = sum(bool(s.completed_at) for _, s in items)
        self.query_one("#library-stats", Static).update(
            f"{len(items)} puzzles  ·  {solved} solved  ·  Your next rabbit hole awaits"
        )
        if not items:
            await shelf.mount(
                Static(
                    "A fresh page. A favorite subject.\n\nCreate your first crossword, "
                    "or try an offline starter below.",
                    id="empty-shelf",
                )
            )
            await shelf.mount(
                Button("Try software engineering", id="starter-software"),
                Button("Take a trip to ancient Rome", id="starter-rome"),
            )
        elif not visible:
            await shelf.mount(Static("No puzzles match this filter."))
        else:
            await shelf.mount(*(PuzzleCard(p, s) for p, s in visible))

    def on_input_changed(self, event: Input.Changed) -> None:
        self.refresh_shelf()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if isinstance(event.button, PuzzleCard):
            self.app.play(event.button.puzzle_id)
        elif event.button.id == "starter-software":
            self.app.push_screen(NewPuzzleScreen("Software engineering", "offline"))
        elif event.button.id == "starter-rome":
            self.app.push_screen(NewPuzzleScreen("Roman history", "offline"))
        elif event.button.id == "new":
            self.action_new()

    def action_new(self) -> None:
        self.app.push_screen(NewPuzzleScreen())

    def action_quit(self) -> None:
        self.app.exit()


class NewPuzzleScreen(Screen):
    BINDINGS = [("escape", "back", "Back to shelf")]

    def __init__(self, topic: str = "", provider: str | None = None):
        super().__init__()
        self.topic, self.provider = topic, provider
        self.busy = False
        self.generation_worker = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="new-form"):
            yield Static("A NEW RABBIT HOLE", classes="eyebrow")
            yield Static("What are you curious about?", classes="page-title")
            yield Static(
                "From Roman roads to recursive functions. Make it your crossword.", classes="muted"
            )
            yield Label("SUBJECT")
            yield Input(
                value=self.topic,
                placeholder="e.g. Software engineering, Roman history, jazz…",
                max_length=200,
                id="topic",
            )
            yield Label("DIFFICULTY")
            yield Select(
                [
                    ("Easy · direct clues, familiar ideas", "easy"),
                    ("Medium · a little lateral thinking", "medium"),
                    ("Hard · subtle clues, deeper knowledge", "hard"),
                ],
                value="medium",
                allow_blank=False,
                id="difficulty",
            )
            yield Label("LENGTH")
            yield Select(
                [
                    ("Quick · 8 clues", "quick"),
                    ("Standard · 14 clues", "standard"),
                    ("Long · 20 clues", "long"),
                ],
                value="standard",
                allow_blank=False,
                id="size",
            )
            yield Label("PUZZLE MAKER")
            providers = available_providers()
            yield Select(
                [
                    ("Claude · local CLI login", "claude"),
                    ("Codex · local CLI login", "codex"),
                    ("Offline · software engineering / Roman history", "offline"),
                ],
                value=self.provider or providers[0],
                allow_blank=False,
                id="provider",
            )
            yield Static(
                "Connected themed grids with original American-style clues.\n"
                "Claude and Codex use your CLI's existing login and usage limits.",
                classes="muted",
            )
            yield Button("Create crossword", id="generate", variant="primary")
            yield LoadingIndicator(id="loading")
            yield Static("", id="generation-status", markup=False)
            yield Button("Back to shelf", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#loading").display = False
        self.query_one("#topic", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate":
            self.start_generation()
        elif event.button.id == "back":
            self.action_back()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.start_generation()

    def start_generation(self) -> None:
        if self.busy:
            return
        topic = self.query_one("#topic", Input).value.strip()
        if not topic:
            self.query_one("#generation-status", Static).update("Give your puzzle a subject first.")
            return
        self.busy = True
        self.query_one("#generate", Button).disabled = True
        self.query_one("#loading").display = True
        self.query_one("#back", Button).label = "Cancel generation"
        self.query_one("#generation-status", Static).update(
            "Writing clues and weaving the grid… This can take a few minutes."
        )
        values = [
            str(self.query_one(f"#{key}", Select).value)
            for key in ("difficulty", "size", "provider")
        ]
        self.generation_worker = self.make_puzzle(topic, *values)

    @work(exclusive=True)
    async def make_puzzle(self, topic: str, difficulty: str, size: str, provider: str) -> None:
        try:
            avoid = [
                e.answer
                for p, _ in self.app.store.list()
                if p.topic.casefold() == topic.casefold()
                for e in p.entries
            ]
            puzzle = await generate(topic, difficulty, size, provider, avoid=avoid)
            self.app.store.save(puzzle, Progress())
        except (ValueError, OSError, sqlite3.Error) as error:
            self.query_one("#generation-status", Static).update(str(error))
            self.query_one("#loading").display = False
            self.query_one("#generate", Button).disabled = False
            self.query_one("#back", Button).label = "Back to shelf"
            self.busy = False
            return
        self.app.pop_screen()
        self.app.play(puzzle.id)

    def action_back(self) -> None:
        if self.generation_worker:
            self.generation_worker.cancel()
        self.app.pop_screen()


class Clue(Static):
    def __init__(self, entry: Entry):
        super().__init__(
            f"{entry.number:>2}  {entry.clue}", id=f"clue-{entry.key}", classes="clue", markup=False
        )
        self.entry = entry

    def on_click(self) -> None:
        screen = self.screen
        if isinstance(screen, PlayScreen) and not screen.paused:
            screen.session.select_entry(self.entry)
            screen.refresh_play()


class CrosswordGrid(Static):
    can_focus = True

    def __init__(self, session: Session):
        super().__init__(id="grid")
        self.session = session
        self.cell_width, self.cell_height = 6, 3
        self.errors: set[tuple[int, int]] = set()
        self.hidden_grid = False

    def configure_size(self) -> None:
        puzzle = self.session.puzzle
        viewport = self.parent.scrollable_content_region
        # Keep roomy, square proportions when the entire board fits vertically.
        self.cell_height = 3 if puzzle.height * 3 + 1 <= viewport.height else 2
        self.styles.width = puzzle.width * self.cell_width + 1
        self.styles.height = puzzle.height * self.cell_height + 1
        self.refresh(layout=True)

    def render(self) -> Text:
        puzzle, progress = self.session.puzzle, self.session.progress
        if self.hidden_grid:
            return Text("\n  Take your time.\n  Your puzzle is paused.", style="#d4aa73")
        solution = puzzle.solution
        active = set(self.session.entry.cells)
        starts = {(e.row, e.col): e.number for e in puzzle.entries}
        text = Text(no_wrap=True, overflow="crop")
        paper = "#e9e5d8"
        background = "#171d1a"
        superscripts = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

        def horizontal(r: int, c: int) -> bool:
            return 0 <= c < puzzle.width and ((r - 1, c) in solution or (r, c) in solution)

        def vertical(r: int, c: int) -> bool:
            return 0 <= r < puzzle.height and ((r, c - 1) in solution or (r, c) in solution)

        def colors(cell: tuple[int, int]) -> tuple[str, str]:
            bg, fg = paper, "#26322e"
            if cell not in solution:
                return background, fg
            key = progress.cell_key(cell)
            if cell in active:
                bg = "#b5c9af"
            if cell == progress.cursor:
                bg, fg = "#e3b875", "#17231e"
            if key in progress.pencil:
                fg = "#6a737d"
            if key in progress.revealed:
                fg = "#7354a0"
            if cell in self.errors:
                bg, fg = "#c46858", "#ffffff"
            return bg, fg

        def edge_style(*neighbors: tuple[int, int]) -> str:
            # Shared edges belong to the strongest adjacent highlight. Taking the first
            # open neighbor makes a down answer narrower wherever an across word joins it.
            # Match the interior precedence: checked error > cursor > selected answer.
            def priority(cell: tuple[int, int]) -> int:
                if cell not in solution:
                    return -1
                if cell in self.errors:
                    return 3
                if cell == progress.cursor:
                    return 2
                return 1 if cell in active else 0

            cell = max(neighbors, key=priority)
            return f"#7d8878 on {colors(cell)[0]}"

        # Junctions join real edges, including corners around the freeform silhouette.
        junctions = {
            (False, True, False, True): "┌",
            (True, False, False, True): "┐",
            (False, True, True, False): "└",
            (True, False, True, False): "┘",
            (True, True, False, True): "┬",
            (True, True, True, False): "┴",
            (False, True, True, True): "├",
            (True, False, True, True): "┤",
            (True, True, True, True): "┼",
            (True, True, False, False): "─",
            (False, False, True, True): "│",
        }
        for r in range(puzzle.height + 1):
            for c in range(puzzle.width + 1):
                edges = (horizontal(r, c - 1), horizontal(r, c), vertical(r - 1, c), vertical(r, c))
                text.append(
                    junctions.get(edges, " "),
                    style=edge_style((r, c), (r, c - 1), (r - 1, c), (r - 1, c - 1)),
                )
                if c < puzzle.width:
                    text.append(
                        "─" * 5 if horizontal(r, c) else " " * 5,
                        style=edge_style((r, c), (r - 1, c)),
                    )
            if r == puzzle.height:
                break
            text.append("\n")
            for line in range(self.cell_height - 1):
                for c in range(puzzle.width):
                    text.append(
                        "│" if vertical(r, c) else " ", style=edge_style((r, c), (r, c - 1))
                    )
                    cell = (r, c)
                    if cell not in solution:
                        text.append(" " * 5, style=f"on {background}")
                        continue
                    key = progress.cell_key(cell)
                    letter = progress.letters.get(key, "") or " "
                    bg, fg = colors(cell)
                    number = str(starts.get(cell, "")).translate(superscripts)
                    if self.cell_height == 3:
                        if line == 0:
                            text.append(f"{number:<5}", style=f"#5d6659 on {bg}")
                        else:
                            text.append(f"  {letter}  ", style=f"bold {fg} on {bg}")
                    else:
                        text.append(f"{number:<2}", style=f"#5d6659 on {bg}")
                        text.append(f"{letter}  ", style=f"bold {fg} on {bg}")
                text.append(
                    "│" if vertical(r, puzzle.width) else " ",
                    style=edge_style((r, puzzle.width - 1)),
                )
                text.append("\n")
        return text

    def on_key(self, event: events.Key) -> None:
        # Handle gameplay and its shortcuts in the same FIFO queue. Priority app bindings
        # can otherwise overtake a letter still bubbling from a focused widget.
        screen = self.screen
        action = next((b.action for b in screen.BINDINGS if b.key == event.key), None)
        if event.key == "ctrl+q":
            self.app.action_quit()
        elif action:
            getattr(screen, f"action_{action}")()
        else:
            screen.on_key(event)
            return
        event.prevent_default()
        event.stop()

    def on_click(self, event: events.Click) -> None:
        if self.hidden_grid:
            return
        # Borders are shared geometry, not input targets.
        if event.x % self.cell_width == 0 or event.y % self.cell_height == 0:
            return
        cell = (event.y // self.cell_height, event.x // self.cell_width)
        if cell not in self.session.puzzle.solution:
            return
        if cell == self.session.progress.cursor:
            self.session.toggle_direction()
        else:
            self.session.select_cell(cell)
        self.screen.refresh_play()


class PlayScreen(Screen):
    BINDINGS = [
        Binding("escape", "shelf", "Shelf"),
        Binding("tab", "next_clue", "Next clue"),
        Binding("shift+tab", "previous_clue", "Previous", show=False),
        Binding("space", "switch", "Across/down"),
        Binding("f2", "pause", "Pause"),
        Binding("ctrl+p", "pencil", "Pencil"),
        Binding("ctrl+k", "check", "Check word"),
        Binding("ctrl+r", "reveal", "Reveal"),
        Binding("f1", "help", "Help"),
    ]

    def __init__(self, puzzle: Puzzle, progress: Progress):
        super().__init__()
        self.session = Session(puzzle, progress)
        self.paused = False
        self.pencil = progress.pencil_mode
        self.last_selected = ""
        self.save_failed = False

    def compose(self) -> ComposeResult:
        puzzle = self.session.puzzle
        with Horizontal(id="play-header"):
            yield Static("CROSSTHEME", id="play-brand")
            yield Static(
                f"{puzzle.topic}  /  {puzzle.difficulty.upper()}", id="play-topic", markup=False
            )
            yield Static("00:00", id="clock")
        yield Static("", id="active-clue", markup=False)
        with Horizontal(id="play-body"):
            with VerticalScroll(id="grid-scroll"):
                yield CrosswordGrid(self.session)
            with VerticalScroll(id="clues"):
                for direction in ("across", "down"):
                    yield Static(direction.upper(), classes="clue-heading")
                    for entry in puzzle.entries:
                        if entry.direction == direction:
                            yield Clue(entry)
        yield Static("", id="play-status", markup=False)
        yield Static(
            "Type letters · Arrows move · Backspace erases · F1 for all controls", id="key-hint"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.resize_layout()
        self.refresh_play()
        self.set_interval(1, self.heartbeat)

    def on_resize(self) -> None:
        if self.is_mounted:
            self.resize_layout()

    def resize_layout(self) -> None:
        board_width = self.session.puzzle.width * 6 + 1
        narrow = self.app.size.width < max(100, board_width + 38)
        self.set_class(narrow, "narrow")
        self.query_one("#grid-scroll").styles.width = "100%" if narrow else board_width + 2
        self.call_after_refresh(self.fit_grid)

    def fit_grid(self) -> None:
        self.query_one(CrosswordGrid).configure_size()
        self.last_selected = ""
        self.call_after_refresh(self.refresh_play)

    def persist(self) -> None:
        try:
            self.app.store.save(self.session.puzzle, self.session.progress)
            self.save_failed = False
        except (OSError, sqlite3.Error) as error:
            if not self.save_failed:
                self.app.notify(
                    f"Save failed: {error}. Keep this session open and free disk space.",
                    severity="error",
                    timeout=15,
                )
            self.save_failed = True

    def heartbeat(self) -> None:
        if self.app.screen is not self:
            return
        self.session.tick()
        self.persist()
        self.refresh_status()

    def refresh_status(self) -> None:
        p, s = self.session.puzzle, self.session.progress
        self.query_one("#clock", Static).update(format_time(s.elapsed))
        if s.completed_at:
            assistance = "Assisted" if s.checks or s.revealed else "Unassisted"
            mode = f"SOLVED in {format_time(s.elapsed)} · {assistance}"
        elif self.paused:
            mode = "PAUSED · F2 to return"
        else:
            mode = "PENCIL" if self.pencil else "INK"
        saved = "SAVE FAILED" if self.save_failed else "Saved locally"
        status = f"{mode}  ·  {s.filled(p)}/{len(p.solution)} squares  ·  {saved}"
        self.query_one("#play-status", Static).update(status)

    def refresh_play(self) -> None:
        session = self.session
        entry = session.entry
        grid = self.query_one(CrosswordGrid)
        grid.hidden_grid = self.paused
        grid.refresh()
        self.query_one("#active-clue", Static).update(
            "PAUSED  ·  A little breathing room. Press F2 when you're ready."
            if self.paused
            else f"{entry.number} {entry.direction.upper()}  /  {entry.clue}  ({len(entry.answer)})"
        )
        self.query_one("#clues").styles.visibility = "hidden" if self.paused else "visible"
        for clue in self.query(Clue):
            clue.set_class(clue.entry.key == entry.key, "selected")
            # Filled is a progress indicator, never an implicit correctness check.
            clue.set_class(
                all(session.progress.letters.get(Progress.cell_key(c)) for c in clue.entry.cells),
                "filled",
            )
        if self.last_selected != entry.key:
            self.query_one(f"#clue-{entry.key}").scroll_visible(animate=False)
            self.last_selected = entry.key
        r, c = session.progress.cursor
        self.query_one("#grid-scroll").scroll_to_region(
            Region(
                grid.virtual_region.x + c * grid.cell_width,
                grid.virtual_region.y + r * grid.cell_height,
                grid.cell_width + 1,
                grid.cell_height + 1,
            ),
            animate=False,
            spacing=None,
        )
        self.refresh_status()
        grid.focus(scroll_visible=False)

    def on_key(self, event: events.Key) -> None:
        if self.paused:
            return
        moves = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
        if event.key in moves:
            self.session.move(*moves[event.key])
        elif event.key in ("backspace", "delete"):
            self.query_one(CrosswordGrid).errors.discard(self.session.progress.cursor)
            self.session.erase(back=event.key == "backspace")
        elif (
            event.character
            and len(event.character) == 1
            and event.character.isascii()
            and event.character.isalpha()
        ):
            self.query_one(CrosswordGrid).errors.discard(self.session.progress.cursor)
            completed = self.session.type_letter(event.character, self.pencil)
            if completed:
                self.celebrate()
            elif self.session.progress.filled(self.session.puzzle) == len(
                self.session.puzzle.solution
            ):
                self.app.notify(
                    "The grid is full, but something is still off. Keep exploring, or check a word."
                )
        else:
            return
        event.prevent_default()
        event.stop()
        self.persist()
        self.refresh_play()

    def celebrate(self) -> None:
        self.persist()
        s = self.session.progress
        self.app.push_screen(
            MessageDialog(
                "EVERYTHING CLICKS.",
                f"You solved {self.session.puzzle.title} in {format_time(s.elapsed)}.\n\n"
                f"{len(self.session.puzzle.entries)} clues connected. "
                "A little more of the world explored.\n"
                f"{s.checks} checks · {len(s.revealed)} revealed squares\n\n"
                "Your finish is saved. Browse the clues, or press Esc to return to your shelf.",
            )
        )

    def action_next_clue(self) -> None:
        if not self.paused:
            self.session.next_entry()
            self.refresh_play()
            self.persist()

    def action_previous_clue(self) -> None:
        if not self.paused:
            self.session.next_entry(-1)
            self.refresh_play()
            self.persist()

    def action_switch(self) -> None:
        if not self.paused:
            self.session.toggle_direction()
            self.refresh_play()
            self.persist()

    def action_pencil(self) -> None:
        self.pencil = not self.pencil
        self.session.progress.pencil_mode = self.pencil
        self.persist()
        self.refresh_status()

    def action_pause(self) -> None:
        if self.session.progress.completed_at:
            return
        self.paused = not self.paused
        if self.paused:
            self.session.pause()
        else:
            self.session.resume()
        self.persist()
        self.refresh_play()

    def action_check(self) -> None:
        if self.paused or self.session.progress.completed_at:
            return
        cells = self.session.entry.cells
        errors = self.session.progress.check(self.session.puzzle, cells)
        self.query_one(CrosswordGrid).errors = errors
        self.persist()
        self.refresh_play()
        self.app.notify(
            f"{len(errors)} incorrect filled squares marked."
            if errors
            else "The filled squares in this word look good."
        )

    def action_reveal(self) -> None:
        if self.paused or self.session.progress.completed_at:
            return
        self.session.pause()
        self.app.push_screen(
            MessageDialog(
                "A little nudge?",
                "Reveal the selected letter? It will be marked in purple, "
                "and this solve will be recorded as assisted.",
                confirm=True,
            ),
            self.reveal_result,
        )

    def reveal_result(self, confirmed: bool) -> None:
        self.session.resume()
        if confirmed:
            self.session.progress.reveal(self.session.puzzle, [self.session.progress.cursor])
            self.query_one(CrosswordGrid).errors.discard(self.session.progress.cursor)
            if self.session.finish_if_correct():
                self.celebrate()
            self.persist()
        self.refresh_play()

    def action_help(self) -> None:
        self.session.pause()
        explanation = self.session.entry.explanation if self.session.progress.completed_at else ""
        self.app.push_screen(
            MessageDialog(
                "MAKE YOURSELF AT HOME",
                "Letters      Fill a square (Q and H are letters, too)\n"
                "Arrows       Move; change direction first at a crossing\n"
                "Space        Switch across / down\n"
                "Tab / Shift+Tab   Next / previous clue\n"
                "Backspace    Erase; move back when already empty\n"
                "Delete       Erase the current square\n"
                "Ctrl+P       Toggle pencil marks\n"
                "Ctrl+K       Check the current word (marks solve assisted)\n"
                "Ctrl+R       Reveal one letter, with confirmation\n"
                "F2           Pause / resume (hides the puzzle)\n"
                "Esc          Save and return to shelf\n"
                "Ctrl+Q       Save and quit\n"
                "Mouse        Select a square or clue\n\n"
                "Cluecraft: tense and number agree. Abbreviations and foreign words are signaled. "
                "A question mark suggests wordplay. "
                "Spaces and punctuation are omitted in answers.\n\n"
                "Filled clues are dimmed without judging correctness. "
                "Purple letters were revealed. "
                "Time pauses on the shelf, in dialogs, or while explicitly paused."
                + (f"\n\nBehind this clue: {explanation}" if explanation else ""),
            ),
            self.help_closed,
        )

    def help_closed(self, _: bool) -> None:
        if not self.paused:
            self.session.resume()

    def action_shelf(self) -> None:
        self.session.pause()
        self.persist()
        if not self.save_failed:
            self.app.pop_screen()
        elif not self.paused:
            self.session.resume()


class CrossthemeApp(App):
    ENABLE_COMMAND_PALETTE = False
    TITLE = "Crosstheme"
    CSS_PATH = "app.tcss"
    BINDINGS = [Binding("ctrl+q", "quit", "Quit", show=False)]

    def __init__(self, store: Store | None = None, puzzle_id: str | None = None):
        super().__init__()
        self.store = store or Store()
        self.initial_puzzle_id = puzzle_id

    def on_mount(self) -> None:
        self.theme = "textual-dark"
        self.push_screen(LibraryScreen())
        if self.initial_puzzle_id:
            self.play(self.initial_puzzle_id)

    def play(self, puzzle_id: str) -> None:
        puzzle, progress = self.store.load(puzzle_id)
        self.push_screen(PlayScreen(puzzle, progress))

    def action_quit(self) -> None:
        # Drain keys already forwarded to the focused screen before taking the final snapshot.
        self.call_after_refresh(self.save_and_quit)

    def save_and_quit(self) -> None:
        for screen in self.screen_stack:
            if isinstance(screen, PlayScreen):
                was_running = screen.session.running
                screen.session.pause()
                screen.persist()
                if screen.save_failed:
                    if was_running:
                        screen.session.resume()
                    return
        self.exit()

    def on_unmount(self) -> None:
        for screen in self.screen_stack:
            if isinstance(screen, PlayScreen):
                screen.session.pause()
                screen.persist()


def run(path: Path | None = None, puzzle_id: str | None = None) -> None:
    store = Store(path)
    try:
        CrossthemeApp(store, puzzle_id).run()
    finally:
        store.close()
