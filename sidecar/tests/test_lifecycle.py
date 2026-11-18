from pathlib import Path

import pytest

from slopr_sidecar.lifecycle import POINTS, fire, load_hooks


def write(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return path


# A hook file that keeps the transcript in a module variable and outputs it instead.
STATEFUL = """
raw = ""

def on_transcribed(t):
    global raw
    raw = t

def on_cleaned(t):
    return raw
"""


def test_loads_hooks_in_filename_order(tmp_path: Path):
    write(tmp_path / "b.py", "def on_cleaned(t): return t + ' b'")
    write(tmp_path / "a.py", "def on_cleaned(t): return t + ' a'\ndef on_logged(t): pass")
    hooks = load_hooks(tmp_path)
    assert [len(hooks[p]) for p in POINTS] == [0, 2, 1]
    assert fire(hooks, "on_cleaned", "hello") == "hello a b"


def test_missing_directory_has_no_hooks(tmp_path: Path):
    assert load_hooks(tmp_path / "missing") == {p: [] for p in POINTS}


def test_file_failing_to_import_is_logged_and_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    write(tmp_path / "a.py", "import nonexistent_module")
    write(tmp_path / "b.py", "def on_logged(t): pass")
    hooks = load_hooks(tmp_path)
    assert len(hooks["on_logged"]) == 1
    assert "a.py failed to load" in caplog.text
    assert "ModuleNotFoundError" in caplog.text


def test_returned_str_replaces_the_text_and_none_keeps_it():
    hooks = {"on_cleaned": [lambda t: "shouted " + t.upper(), lambda t: None]}
    assert fire(hooks, "on_cleaned", "hello") == "shouted HELLO"


def test_hook_file_keeps_state_between_its_hooks(tmp_path: Path):
    write(tmp_path / "a.py", STATEFUL)
    hooks = load_hooks(tmp_path)
    fire(hooks, "on_transcribed", "um hello")
    assert fire(hooks, "on_cleaned", "Hello.") == "um hello"


def test_on_logged_return_values_are_ignored():
    calls = []
    hooks = {"on_logged": [lambda t: "", calls.append]}
    fire(hooks, "on_logged", "hello")
    assert calls == ["hello"]


def test_failing_hook_is_logged_and_later_hooks_still_run(caplog: pytest.LogCaptureFixture):
    def broken(t: str) -> str:
        raise RuntimeError("boom")

    hooks = {"on_cleaned": [broken, lambda t: t + "!"]}
    assert fire(hooks, "on_cleaned", "hello") == "hello!"
    assert "on_cleaned hook failed" in caplog.text
    assert "RuntimeError: boom" in caplog.text


def test_fire_stops_once_the_text_is_empty():
    calls = []
    hooks = {"on_transcribed": [lambda t: "", calls.append]}
    assert fire(hooks, "on_transcribed", "hello") == ""
    assert fire(hooks, "on_transcribed", "") == ""
    assert calls == []
