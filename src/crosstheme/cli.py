"""Small CLI entry point; the interactive app is loaded only when needed."""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

from crosstheme.engine import Progress, format_time
from crosstheme.providers import available_providers, generate
from crosstheme.storage import Store, default_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Crosstheme — crosswords for curious minds")
    parser.add_argument("--data-dir", type=Path, help="Override the local puzzle library directory")
    parser.add_argument("--version", action="version", version="crosstheme 0.1.0")
    sub = parser.add_subparsers(dest="command")
    new = sub.add_parser("new", help="Generate and save a puzzle, then play")
    new.add_argument("topic")
    new.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    new.add_argument("--size", choices=["quick", "standard", "long"], default="standard")
    new.add_argument("--provider", choices=["auto", "claude", "codex", "offline"], default="auto")
    new.add_argument("--model", help="Optional model name passed to the selected CLI")
    new.add_argument(
        "--seed", type=int, help="Reproducible grid arrangement for the same candidate pool"
    )
    new.add_argument("--no-play", action="store_true", help="Generate without opening the TUI")
    sub.add_parser("list", help="List saved puzzles")
    play = sub.add_parser("play", help="Resume or revisit a saved puzzle")
    play.add_argument("id", help="Puzzle ID or unique prefix")
    export = sub.add_parser("export", help="Export a portable JSON puzzle (includes answers)")
    export.add_argument("id")
    export.add_argument("--output", type=Path, required=True)
    sub.add_parser("doctor", help="Show available providers and data location")
    args = parser.parse_args()
    path = args.data_dir / "puzzles.sqlite3" if args.data_dir else default_path()
    if args.command == "doctor":
        print(f"Library: {path}\nProviders on PATH: {', '.join(available_providers())}")
        print(
            "For online generation, sign in with `claude` or `codex login` first.\n"
            "Offline supports Software engineering and Roman history."
        )
        return
    try:
        puzzle_id = None
        if args.command:
            store = Store(path)
            try:
                if args.command == "new":
                    print(f"Creating a {args.difficulty} crossword about {args.topic}…", flush=True)
                    avoid = [
                        e.answer
                        for p, _ in store.list()
                        if p.topic.casefold() == args.topic.casefold()
                        for e in p.entries
                    ]
                    puzzle = asyncio.run(
                        generate(
                            args.topic,
                            args.difficulty,
                            args.size,
                            args.provider,
                            args.seed,
                            args.model,
                            avoid,
                        )
                    )
                    store.save(puzzle, Progress())
                    print(f"Saved {puzzle.id} · {puzzle.title} · {len(puzzle.entries)} clues")
                    if args.no_play:
                        return
                    puzzle_id = puzzle.id
                elif args.command == "list":
                    for p, s in store.list():
                        status = (
                            "solved" if s.completed_at else "playing" if s.filled(p) else "ready"
                        )
                        print(
                            f"{p.id}  {p.difficulty:6}  {status:7}  "
                            f"{format_time(s.elapsed)}  {p.title}"
                        )
                    return
                else:
                    matches = [p for p, _ in store.list() if p.id.startswith(args.id)]
                    if len(matches) != 1:
                        raise ValueError("Use a unique puzzle ID or prefix from `crosstheme list`")
                    puzzle_id = matches[0].id
                    if args.command == "export":
                        # Exclusive create avoids silently overwriting an existing export.
                        with args.output.open("x") as file:
                            json.dump(matches[0].to_dict(), file, indent=2)
                            file.write("\n")
                        print(f"Exported puzzle including answers to {args.output}")
                        return
            finally:
                store.close()
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError(
                "Open Crosstheme in an interactive terminal, or use `new --no-play` / `list`."
            )
        from crosstheme.app import run

        run(path, puzzle_id)
    except (ValueError, KeyError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"crosstheme: {error}\n")
    except KeyboardInterrupt:
        parser.exit(130, "\nCancelled.\n")
