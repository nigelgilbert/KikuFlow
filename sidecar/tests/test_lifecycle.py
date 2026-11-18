from datetime import datetime
from pathlib import Path

import pytest

from slopr_sidecar.lifecycle import Utterance, fire, load_hooks


def write(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return path


def utterance(text: str = "hello") -> Utterance:
    return Utterance(datetime.now().astimezone(), text, text)


def test_loads_hooks_in_filename_order_and_skips_missing_dirs(tmp_path: Path):
    write(tmp_path / "a/b.py", "def on_cleaned(u): return u.text + ' b'")
    write(tmp_path / "c/a.py", "def on_cleaned(u): return u.text + ' a'\ndef on_logged(u): pass")
    hooks = load_hooks([tmp_path / "a", tmp_path / "missing", tmp_path / "c"])
    assert [len(hooks[p]) for p in ("on_transcribed", "on_cleaned", "on_logged")] == [0, 2, 1]
    u = utterance()
    fire(hooks, "on_cleaned", u)
    assert u.text == "hello a b"


def test_user_file_replaces_builtin_of_the_same_name(tmp_path: Path):
    imported = tmp_path / "imported"
    builtin = f"open({str(imported)!r}, 'w')\ndef on_logged(u): pass"
    write(tmp_path / "builtin/log.py", builtin)
    write(tmp_path / "user/log.py", "")
    hooks = load_hooks([tmp_path / "builtin", tmp_path / "user"])
    assert hooks == {"on_transcribed": [], "on_cleaned": [], "on_logged": []}
    assert not imported.exists()


def test_file_failing_to_import_is_logged_and_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    write(tmp_path / "a.py", "import nonexistent_module")
    write(tmp_path / "b.py", "def on_logged(u): pass")
    hooks = load_hooks([tmp_path])
    assert len(hooks["on_logged"]) == 1
    assert "a.py failed to load" in caplog.text
    assert "ModuleNotFoundError" in caplog.text


def test_fire_replaces_text_on_str_keeps_it_on_none_and_never_touches_raw():
    hooks = {"on_cleaned": [lambda u: "shouted " + u.text.upper(), lambda u: None]}
    u = utterance()
    fire(hooks, "on_cleaned", u)
    assert (u.raw, u.text) == ("hello", "shouted HELLO")


def test_on_logged_return_values_are_ignored():
    calls = []
    hooks = {"on_logged": [lambda u: "", lambda u: calls.append(u.text)]}
    fire(hooks, "on_logged", utterance())
    assert calls == ["hello"]


def test_failing_hook_is_logged_and_later_hooks_still_run(caplog: pytest.LogCaptureFixture):
    def broken(u: Utterance) -> str:
        raise RuntimeError("boom")

    hooks = {"on_cleaned": [broken, lambda u: u.text + "!"]}
    u = utterance()
    fire(hooks, "on_cleaned", u)
    assert u.text == "hello!"
    assert "on_cleaned hook failed" in caplog.text
    assert "RuntimeError: boom" in caplog.text


def test_fire_stops_once_the_text_is_empty():
    calls = []
    hooks = {"on_transcribed": [lambda u: "", calls.append]}
    u = utterance()
    fire(hooks, "on_transcribed", u)
    assert (u.text, calls) == ("", [])
    fire(hooks, "on_transcribed", u)
    assert calls == []
