import asyncio
import json
import os
import sys

import pytest

from crosstheme.providers import (
    GenerationError,
    generate,
    parse_candidates,
    prompt_for,
    run_provider,
)

DATA = {
    "title": "Test",
    "entries": [{"answer": "CACHE", "clue": "A fast store", "explanation": "Stores reusable data"}],
}


@pytest.mark.parametrize(
    "raw",
    [
        json.dumps(DATA),
        f"```json\n{json.dumps(DATA)}\n```",
        json.dumps({"structured_output": DATA}),
        json.dumps({"result": json.dumps(DATA)}),
    ],
)
def test_provider_output_wrappers(raw):
    title, entries = parse_candidates(raw)
    assert title == "Test" and entries[0].answer == "CACHE"


@pytest.mark.parametrize(
    "raw", ["nonsense", "[]", '{"entries": []}', '{"is_error":true,"result":"Login required"}']
)
def test_invalid_outputs(raw):
    with pytest.raises(GenerationError):
        parse_candidates(raw)


@pytest.mark.parametrize("result", [None, 42, [], {}, True])
def test_malformed_result_wrapper_is_a_generation_error(result):
    with pytest.raises(GenerationError, match="text"):
        parse_candidates(json.dumps({"result": result}))


def test_filters_duplicate_giveaway_invalid_and_control_characters():
    data = {
        **DATA,
        "entries": DATA["entries"] * 2
        + [
            {"answer": "API", "clue": "API endpoint"},
            {"answer": "B2B", "clue": "Commerce"},
            {"answer": "BAD", "clue": "A\x1b[31mcontrol"},
        ],
    }
    assert len(parse_candidates(json.dumps(data))[1]) == 1
    assert "Monday-like" in prompt_for("Software", "easy", "quick")
    assert "Friday/Saturday-like" in prompt_for("Software", "hard", "quick")
    assert "question mark" in prompt_for("Software", "hard", "quick")


def fake_executable(tmp_path, monkeypatch, code):
    path = tmp_path / "fake-cli"
    path.write_text(f"#!{sys.executable}\n" + code)
    path.chmod(0o755)
    monkeypatch.setattr("crosstheme.providers.shutil.which", lambda _: str(path))


async def test_claude_subprocess_protocol(tmp_path, monkeypatch):
    fake_executable(
        tmp_path,
        monkeypatch,
        "import json,sys\n"
        "assert '--tools' in sys.argv and sys.argv[sys.argv.index('--tools')+1] == ''\n"
        "assert sys.stdin.read() == 'test prompt'\n"
        f"print({json.dumps({'structured_output': DATA})!r})\n",
    )
    result = await run_provider("claude", "test prompt")
    assert parse_candidates(result)[0] == "Test"


async def test_codex_subprocess_output_file(tmp_path, monkeypatch):
    fake_executable(
        tmp_path,
        monkeypatch,
        "import pathlib,sys\n"
        "assert sys.argv[1] == 'exec' and 'read-only' in sys.argv\n"
        "assert sys.stdin.read() == 'test prompt'\n"
        f"pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text({json.dumps(DATA)!r})\n",
    )
    assert parse_candidates(await run_provider("codex", "test prompt"))[0] == "Test"


async def test_timeout_and_missing_provider(tmp_path, monkeypatch):
    fake_executable(tmp_path, monkeypatch, "import time\ntime.sleep(30)\n")
    with pytest.raises(GenerationError, match="timed out"):
        await run_provider("claude", "test", timeout=0.05)
    monkeypatch.setattr("crosstheme.providers.shutil.which", lambda _: None)
    with pytest.raises(GenerationError, match="PATH"):
        await run_provider("claude", "test")


async def test_cancellation_terminates_process(tmp_path, monkeypatch):
    pidfile = tmp_path / "pid"
    fake_executable(
        tmp_path,
        monkeypatch,
        "import pathlib,os,time\n"
        f"pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(30)\n",
    )
    task = asyncio.create_task(run_provider("claude", "test"))
    for _ in range(100):
        if pidfile.exists():
            break
        await asyncio.sleep(0.01)
    assert pidfile.exists()
    pid = int(pidfile.read_text())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


async def test_offline_unknown_theme_never_silently_substitutes():
    with pytest.raises(ValueError, match="Offline themes"):
        await generate("Astronomy", provider="offline")
    with pytest.raises(GenerationError, match="topic"):
        await generate("\n", provider="offline")
