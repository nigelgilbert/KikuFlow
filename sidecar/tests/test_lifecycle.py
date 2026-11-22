from pathlib import Path

import pytest

from kiku_sidecar import lifecycle
from kiku_sidecar.lifecycle import (
    POINTS,
    Hook,
    default_message,
    fire,
    fire_done,
    labelled,
    load_hooks,
    report,
)

HERE = Path(__file__)


def recorder(calls: list[str]) -> Hook:
    """Return a hook that adds its text to `calls` and returns it."""

    def record(t: str) -> str:
        calls.append(t)
        return t

    return record


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
    return t

def on_cleaned(t):
    return raw
"""


def test_loads_hooks_in_filename_order(tmp_path: Path):
    write(tmp_path / "b.py", "def on_cleaned(t): return t + ' b'")
    write(tmp_path / "a.py", "def on_cleaned(t): return t + ' a'\ndef on_done(t): return t")
    hooks = load_hooks(tmp_path)
    assert [len(hooks[p]) for p in POINTS] == [0, 2, 0, 1]
    assert fire(hooks, "on_cleaned", "hello") == "hello a b"


def test_missing_directory_has_no_hooks(tmp_path: Path):
    assert load_hooks(tmp_path / "missing") == {p: [] for p in (*POINTS, "on_error")}


def test_file_failing_to_import_raises_labelled(tmp_path: Path):
    write(tmp_path / "voice.py", "import nonexistent_module")
    with pytest.raises(ModuleNotFoundError) as info:
        load_hooks(tmp_path)
    assert default_message(info.value) == (
        "hook file voice.py: ModuleNotFoundError: No module named 'nonexistent_module'"
    )


def test_returned_str_replaces_the_text():
    hooks = {"on_cleaned": [(HERE, lambda t: "shouted " + t.upper()), (HERE, lambda t: t + "!")]}
    assert fire(hooks, "on_cleaned", "hello") == "shouted HELLO!"


def test_hook_returning_nothing_raises_labelled(tmp_path: Path):
    write(tmp_path / "a.py", "def on_cleaned(t):\n    t.upper()\n")
    with pytest.raises(TypeError) as info:
        fire(load_hooks(tmp_path), "on_cleaned", "hello")
    assert default_message(info.value) == (
        "on_cleaned in a.py: TypeError: on_cleaned returned NoneType, not str"
    )


def test_hook_file_keeps_state_between_its_hooks(tmp_path: Path):
    write(tmp_path / "a.py", STATEFUL)
    hooks = load_hooks(tmp_path)
    fire(hooks, "on_transcribed", "um hello")
    assert fire(hooks, "on_cleaned", "Hello.") == "um hello"


def test_on_done_return_values_are_ignored():
    calls = []
    hooks = {"on_done": [(HERE, lambda t: ""), (HERE, recorder(calls))]}
    fire_done(hooks, "hello")
    assert calls == ["hello"]


def test_failing_hook_raises_labelled_and_later_hooks_do_not_run(tmp_path: Path):
    calls = []
    write(tmp_path / "voice.py", "def on_cleaned(t):\n    return {}['x']\n")
    hooks = load_hooks(tmp_path)
    hooks["on_cleaned"].append((HERE, recorder(calls)))
    with pytest.raises(KeyError) as info:
        fire(hooks, "on_cleaned", "hello")
    assert info.value.__notes__ == ["on_cleaned in voice.py:2"]
    assert default_message(info.value) == "on_cleaned in voice.py:2: KeyError: 'x'"
    assert calls == []


def test_label_has_no_line_without_a_frame_in_the_hook_file(tmp_path: Path):
    def broken(t: str) -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError) as info:
        fire({"on_cleaned": [(tmp_path / "voice.py", broken)]}, "on_cleaned", "hello")
    assert default_message(info.value) == "on_cleaned in voice.py: RuntimeError: boom"


def test_message_without_text_has_no_trailing_colon():
    with pytest.raises(TimeoutError) as info, labelled("cleanup model"):
        raise TimeoutError
    assert default_message(info.value) == "cleanup model: TimeoutError"


def test_message_of_only_whitespace_has_no_trailing_colon():
    with pytest.raises(RuntimeError) as info, labelled("cleanup model"):
        raise RuntimeError("\n")
    assert default_message(info.value) == "cleanup model: RuntimeError"


def test_message_is_folded_onto_one_line():
    with pytest.raises(ValueError) as info, labelled("speech recognition"):
        raise ValueError("first line\n  second line")
    assert default_message(info.value) == "speech recognition: ValueError: first line second line"


def test_fire_stops_once_the_text_is_empty():
    calls = []
    hooks = {"on_transcribed": [(HERE, lambda t: ""), (HERE, recorder(calls))]}
    assert fire(hooks, "on_transcribed", "hello") == ""
    assert fire(hooks, "on_transcribed", "") == ""
    assert calls == []


@pytest.fixture
def errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temporary errors.txt."""
    monkeypatch.setattr(lifecycle, "ERRORS", tmp_path / "errors.txt")
    return tmp_path / "errors.txt"


def entries(errors: Path) -> list[str]:
    """The entries of errors.txt without their time."""
    text = errors.read_text() if errors.exists() else ""
    return [entry[17:] for entry in filter(None, text.split("\n\n"))]


def labelled_error() -> KeyError:
    with pytest.raises(KeyError) as info, labelled("on_cleaned in voice.py:3"):
        raise KeyError("x")
    return info.value


def test_on_error_loads_beside_the_text_hooks(tmp_path: Path, errors: Path):
    write(tmp_path / "errors.py", "def on_error(e): return 'nope'")
    hooks = load_hooks(tmp_path)
    assert [path.name for path, _ in hooks["on_error"]] == ["errors.py"]
    assert report(hooks, labelled_error()) == "nope"


def test_first_message_from_on_error_wins(tmp_path: Path, errors: Path):
    write(tmp_path / "a.py", "def on_error(e):\n    return f'first:\\n {type(e).__name__}'")
    write(tmp_path / "b.py", "def on_error(e): return 'second'")
    assert report(load_hooks(tmp_path), labelled_error()) == "first: KeyError"
    assert entries(errors) == ["first: KeyError"]


def test_on_error_returning_nothing_is_skipped_and_gives_the_default(tmp_path: Path, errors: Path):
    write(tmp_path / "a.py", "def on_error(e): pass")
    expected = "on_cleaned in voice.py:3: KeyError: 'x'"
    failure = "on_error in a.py: TypeError: on_error returned NoneType, not str"
    assert report(load_hooks(tmp_path), labelled_error()) == expected
    assert entries(errors) == [expected, failure]


def test_no_on_error_hook_gives_the_default(tmp_path: Path, errors: Path):
    expected = "on_cleaned in voice.py:3: KeyError: 'x'"
    assert report(load_hooks(tmp_path / "missing"), labelled_error()) == expected
    assert entries(errors) == [expected]


def test_on_error_returning_empty_suppresses_the_message(tmp_path: Path, errors: Path):
    write(tmp_path / "a.py", "def on_error(e): return ''")
    write(tmp_path / "b.py", "def on_error(e): return 'not reached'")
    assert report(load_hooks(tmp_path), labelled_error()) == ""
    assert not errors.exists()


def test_on_error_gets_the_exception_with_its_type_and_note(tmp_path: Path, errors: Path):
    write(
        tmp_path / "a.py",
        "def on_error(e):\n"
        "    if isinstance(e, KeyError) and 'voice.py:3' in str(e.__notes__):\n"
        "        return 'seen'\n",
    )
    assert report(load_hooks(tmp_path), labelled_error()) == "seen"


def test_raising_on_error_is_skipped_and_recorded(
    tmp_path: Path, errors: Path, caplog: pytest.LogCaptureFixture
):
    write(tmp_path / "a.py", "def on_error(e):\n    raise RuntimeError('broken')")
    write(tmp_path / "b.py", "def on_error(e): return 'next'")
    assert report(load_hooks(tmp_path), labelled_error()) == "next"
    assert "on_error in a.py:2" in caplog.text
    # Its own failure is recorded under the default message, without going through on_error.
    assert entries(errors) == ["next", "on_error in a.py:2: RuntimeError: broken"]


def test_on_error_returning_a_wrong_type_is_skipped_and_recorded(tmp_path: Path, errors: Path):
    write(tmp_path / "offline.py", "def on_error(e): return {}")
    write(tmp_path / "z.py", "def on_error(e): return 'next'")
    assert report(load_hooks(tmp_path), labelled_error()) == "next"
    failure = "on_error in offline.py: TypeError: on_error returned dict, not str"
    assert entries(errors) == ["next", failure]
    (tmp_path / "z.py").unlink()
    default = "on_cleaned in voice.py:3: KeyError: 'x'"
    assert report(load_hooks(tmp_path), labelled_error()) == default
    assert entries(errors) == [default, failure, "next", failure]
