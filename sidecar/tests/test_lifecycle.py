import textwrap
from pathlib import Path
from typing import override

import pytest

from kiku_sidecar import Plugin, lifecycle
from kiku_sidecar.lifecycle import (
    Plugins,
    TextPoint,
    default_message,
    fire,
    fire_done,
    hook_message,
    labelled,
    load_plugins,
    report,
)

HERE = Path(__file__)

# The first four lines of every hook file written by `plugin_file`, so its methods start on line 5.
HEADER = "from kiku_sidecar import Plugin\n\n\nclass P(Plugin):\n"


class Recorder(Plugin):
    """Add the text each hook gets to `calls`, and pass it on."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    @override
    def on_transcribed(self, t: str) -> str:
        self.calls.append(t)
        return t

    @override
    def on_cleaned(self, t: str) -> str:
        self.calls.append(t)
        return t

    @override
    def on_done(self, t: str) -> str:
        self.calls.append(t)
        return t


class Empty(Plugin):
    """Stop the dictation at every text hook, and return an empty string from on_done."""

    @override
    def on_transcribed(self, t: str) -> str:
        return ""

    @override
    def on_done(self, t: str) -> str:
        return ""


class Shout(Plugin):
    @override
    def on_cleaned(self, t: str) -> str:
        return "shouted " + t.upper()


class Exclaim(Plugin):
    @override
    def on_cleaned(self, t: str) -> str:
        return t + "!"


def write(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return path


def plugin_file(methods: str) -> str:
    """Return the source of a hook file whose one plugin, `P`, has `methods`."""
    body = textwrap.indent(textwrap.dedent(methods), "    ")
    return HEADER + body


def test_loads_plugins_in_filename_order(tmp_path: Path):
    write(tmp_path / "b.py", plugin_file("def on_cleaned(self, t: str): return t + ' b'"))
    write(tmp_path / "a.py", plugin_file("def on_cleaned(self, t: str): return t + ' a'"))
    plugins = load_plugins(tmp_path)
    assert [path.name for path, _ in plugins] == ["a.py", "b.py"]
    assert fire(plugins, "on_cleaned", "hello") == "hello a b"


def test_two_plugins_in_one_file_run_in_definition_order(tmp_path: Path):
    source = (
        "from kiku_sidecar import Plugin\n\n\n"
        "class Second(Plugin):\n"
        "    def on_cleaned(self, t: str): return t + ' second'\n\n\n"
        "class First(Plugin):\n"
        "    def on_cleaned(self, t: str): return t + ' first'\n"
    )
    write(tmp_path / "a.py", source)
    plugins = load_plugins(tmp_path)
    assert [type(plugin).__name__ for _, plugin in plugins] == ["Second", "First"]
    assert fire(plugins, "on_cleaned", "hello") == "hello second first"


def test_class_bound_to_two_names_is_instantiated_once(tmp_path: Path):
    source = plugin_file("def on_cleaned(self, t: str): return t + '!'") + "\n\nAlias = P\n"
    write(tmp_path / "a.py", source)
    assert fire(load_plugins(tmp_path), "on_cleaned", "hello") == "hello!"


def test_imported_subclass_is_not_instantiated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    shared = "from kiku_sidecar import Plugin\n\n\nclass Shared(Plugin):\n    pass\n"
    write(tmp_path / "lib/shared.py", shared)
    monkeypatch.syspath_prepend(tmp_path / "lib")
    write(tmp_path / "hooks/a.py", "from shared import Shared\n\n\nclass Own(Shared):\n    pass\n")
    plugins = load_plugins(tmp_path / "hooks")
    assert [type(plugin).__name__ for _, plugin in plugins] == ["Own"]


def test_module_level_hooks_load_no_plugins(tmp_path: Path):
    write(tmp_path / "a.py", "def on_cleaned(t): return t.upper()\ndef on_error(e): return ''\n")
    assert load_plugins(tmp_path) == []


def test_missing_directory_has_no_plugins(tmp_path: Path):
    assert load_plugins(tmp_path / "missing") == []


def test_file_failing_to_import_raises_labelled(tmp_path: Path):
    write(tmp_path / "voice.py", "import nonexistent_module")
    with pytest.raises(ModuleNotFoundError) as info:
        load_plugins(tmp_path)
    assert default_message(info.value) == (
        "hook file voice.py: ModuleNotFoundError: No module named 'nonexistent_module'"
    )


def test_plugin_failing_to_initialize_raises_labelled(tmp_path: Path):
    write(
        tmp_path / "voice.py",
        plugin_file("def __init__(self):\n    raise RuntimeError('no model')"),
    )
    with pytest.raises(RuntimeError) as info:
        load_plugins(tmp_path)
    assert default_message(info.value) == "hook file voice.py: RuntimeError: no model"


def test_defaults_pass_text_and_exceptions_through():
    plugins: Plugins = [(HERE, Plugin())]
    points: tuple[TextPoint, ...] = ("on_transcribed", "on_cleaned", "on_sent")
    for point in points:
        assert fire(plugins, point, "hello") == "hello"
    fire_done(plugins, "hello")
    assert hook_message(plugins, KeyError("x")) is None


def test_returned_str_replaces_the_text():
    plugins: Plugins = [(HERE, Shout()), (HERE, Exclaim())]
    assert fire(plugins, "on_cleaned", "hello") == "shouted HELLO!"


def test_hook_returning_nothing_raises_labelled(tmp_path: Path):
    write(tmp_path / "a.py", plugin_file("def on_cleaned(self, t: str):\n    t.upper()\n"))
    with pytest.raises(TypeError) as info:
        fire(load_plugins(tmp_path), "on_cleaned", "hello")
    assert default_message(info.value) == (
        "on_cleaned in a.py: TypeError: on_cleaned returned NoneType, not str"
    )


def test_state_on_self_persists_between_hooks(tmp_path: Path):
    methods = """
    def __init__(self):
        self.raw = ""

    def on_transcribed(self, t: str):
        self.raw = t
        return t

    def on_cleaned(self, t: str):
        return self.raw
    """
    write(tmp_path / "a.py", plugin_file(methods))
    plugins = load_plugins(tmp_path)
    fire(plugins, "on_transcribed", "um hello")
    assert fire(plugins, "on_cleaned", "Hello.") == "um hello"


def test_module_level_state_persists_between_hooks(tmp_path: Path):
    source = (
        "from kiku_sidecar import Plugin\n\n"
        "seen = []\n\n\n"
        "class P(Plugin):\n"
        "    def on_transcribed(self, t: str):\n"
        "        seen.append(t)\n"
        "        return t\n\n"
        "    def on_cleaned(self, t: str):\n"
        "        return ' '.join(seen)\n"
    )
    write(tmp_path / "a.py", source)
    plugins = load_plugins(tmp_path)
    fire(plugins, "on_transcribed", "um hello")
    assert fire(plugins, "on_cleaned", "Hello.") == "um hello"


def test_on_done_return_values_are_not_used():
    recorder = Recorder()
    fire_done([(HERE, Empty()), (HERE, recorder)], "hello")
    assert recorder.calls == ["hello"]


def test_failing_hook_raises_labelled_and_later_hooks_do_not_run(tmp_path: Path):
    write(tmp_path / "voice.py", plugin_file("def on_cleaned(self, t: str):\n    return {}['x']\n"))
    recorder = Recorder()
    plugins: Plugins = [*load_plugins(tmp_path), (HERE, recorder)]
    with pytest.raises(KeyError) as info:
        fire(plugins, "on_cleaned", "hello")
    assert info.value.__notes__ == ["on_cleaned in voice.py:6"]
    assert default_message(info.value) == "on_cleaned in voice.py:6: KeyError: 'x'"
    assert recorder.calls == []


def test_label_has_no_line_without_a_frame_in_the_hook_file(tmp_path: Path):
    class Broken(Plugin):
        @override
        def on_cleaned(self, t: str) -> str:
            raise RuntimeError("boom")

    plugins: Plugins = [(tmp_path / "voice.py", Broken())]
    with pytest.raises(RuntimeError) as info:
        fire(plugins, "on_cleaned", "hello")
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
    recorder = Recorder()
    plugins: Plugins = [(HERE, Empty()), (HERE, recorder)]
    assert fire(plugins, "on_transcribed", "hello") == ""
    assert fire(plugins, "on_transcribed", "") == ""
    assert recorder.calls == []


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


def on_error_file(body: str) -> str:
    """Return the source of a hook file whose plugin's on_error runs `body`."""
    return plugin_file(f"def on_error(self, e: Exception):\n    {body}\n")


def test_on_error_is_a_method_beside_the_text_hooks(tmp_path: Path, errors: Path):
    methods = """
    def on_cleaned(self, t: str):
        return t

    def on_error(self, e: Exception):
        return 'nope'
    """
    write(tmp_path / "errors.py", plugin_file(methods))
    plugins = load_plugins(tmp_path)
    assert [path.name for path, _ in plugins] == ["errors.py"]
    assert report(plugins, labelled_error()) == "nope"


def test_first_message_from_on_error_wins(tmp_path: Path, errors: Path):
    write(tmp_path / "a.py", on_error_file("return f'first:\\n {type(e).__name__}'"))
    write(tmp_path / "b.py", on_error_file("return 'second'"))
    assert report(load_plugins(tmp_path), labelled_error()) == "first: KeyError"
    assert entries(errors) == ["first: KeyError"]


def test_on_error_returning_nothing_is_skipped_and_gives_the_default(tmp_path: Path, errors: Path):
    write(tmp_path / "a.py", on_error_file("pass"))
    expected = "on_cleaned in voice.py:3: KeyError: 'x'"
    failure = "on_error in a.py: TypeError: on_error returned NoneType, not str or the exception"
    assert report(load_plugins(tmp_path), labelled_error()) == expected
    assert entries(errors) == [expected, failure]


def test_on_error_returning_the_exception_gives_the_default(tmp_path: Path, errors: Path):
    write(tmp_path / "a.py", on_error_file("return e"))
    expected = "on_cleaned in voice.py:3: KeyError: 'x'"
    assert report(load_plugins(tmp_path), labelled_error()) == expected
    assert entries(errors) == [expected]


def test_on_error_returning_the_exception_leaves_it_to_the_next(tmp_path: Path, errors: Path):
    write(tmp_path / "a.py", on_error_file("return e"))
    write(tmp_path / "b.py", on_error_file("return 'second'"))
    assert report(load_plugins(tmp_path), labelled_error()) == "second"
    assert entries(errors) == ["second"]


def test_on_error_returning_another_exception_is_skipped_and_recorded(tmp_path: Path, errors: Path):
    write(tmp_path / "a.py", on_error_file("return ValueError('other')"))
    expected = "on_cleaned in voice.py:3: KeyError: 'x'"
    failure = "on_error in a.py: TypeError: on_error returned ValueError, not str or the exception"
    assert report(load_plugins(tmp_path), labelled_error()) == expected
    assert entries(errors) == [expected, failure]


def test_no_on_error_hook_gives_the_default(tmp_path: Path, errors: Path):
    expected = "on_cleaned in voice.py:3: KeyError: 'x'"
    assert report(load_plugins(tmp_path / "missing"), labelled_error()) == expected
    assert entries(errors) == [expected]


def test_on_error_returning_empty_suppresses_the_message(tmp_path: Path, errors: Path):
    write(tmp_path / "a.py", on_error_file("return ''"))
    write(tmp_path / "b.py", on_error_file("return 'not reached'"))
    assert report(load_plugins(tmp_path), labelled_error()) == ""
    assert not errors.exists()


def test_on_error_gets_the_exception_with_its_type_and_note(tmp_path: Path, errors: Path):
    methods = """
    def on_error(self, e: Exception):
        if isinstance(e, KeyError) and 'voice.py:3' in str(e.__notes__):
            return 'seen'
    """
    write(tmp_path / "a.py", plugin_file(methods))
    assert report(load_plugins(tmp_path), labelled_error()) == "seen"


def test_raising_on_error_is_skipped_and_recorded(
    tmp_path: Path, errors: Path, caplog: pytest.LogCaptureFixture
):
    write(tmp_path / "a.py", on_error_file("raise RuntimeError('broken')"))
    write(tmp_path / "b.py", on_error_file("return 'next'"))
    assert report(load_plugins(tmp_path), labelled_error()) == "next"
    assert "on_error in a.py:6" in caplog.text
    # Its own failure is recorded under the default message, without going through on_error.
    assert entries(errors) == ["next", "on_error in a.py:6: RuntimeError: broken"]


def test_on_error_returning_a_wrong_type_is_skipped_and_recorded(tmp_path: Path, errors: Path):
    write(tmp_path / "offline.py", on_error_file("return {}"))
    write(tmp_path / "z.py", on_error_file("return 'next'"))
    assert report(load_plugins(tmp_path), labelled_error()) == "next"
    failure = "on_error in offline.py: TypeError: on_error returned dict, not str or the exception"
    assert entries(errors) == ["next", failure]
    (tmp_path / "z.py").unlink()
    default = "on_cleaned in voice.py:3: KeyError: 'x'"
    assert report(load_plugins(tmp_path), labelled_error()) == default
    assert entries(errors) == [default, failure, "next", failure]
