"""The plugins in plain .py files and their on_* hooks, the log and errors.txt."""

import logging
import runpy
import traceback
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal

from .config import APP_DIR

log = logging.getLogger(__name__)

HOOK_DIR = APP_DIR / "hooks"
LOG_FILE = APP_DIR / "log.txt"
ERRORS = APP_DIR / "errors.txt"

# The `__module__` of a class that a file run by `runpy.run_path` defines.
RUN_PATH_MODULE = "<run_path>"

type Hook = Callable[[str], str]
type ErrorHook = Callable[[Exception], str | Exception]
# The hooks whose return replaces the text.
type TextPoint = Literal["on_transcribed", "on_cleaned", "on_sent"]


class Plugin:
    """Change a dictation at the points whose hooks a subclass overrides.

    Every hook passes its input on unchanged until it is overridden.
    """

    def on_transcribed(self, t: str) -> str:
        """Return the text the cleanup model sees, given what speech recognition heard.

        An empty string stops the dictation, and nothing is pasted or logged.
        """
        return t

    def on_cleaned(self, t: str) -> str:
        """Return the text to paste, given what the cleanup model wrote.

        An empty string stops the dictation, and nothing is pasted or logged.
        """
        return t

    def on_sent(self, t: str) -> str:
        """Return the log entry, given the text that has gone off to be pasted.

        An empty string keeps the dictation out of the log, and on_done does not fire.
        """
        return t

    def on_done(self, t: str) -> str:
        """Act on the log entry once it is written, and return it. The return is not used."""
        return t

    def on_error(self, e: Exception) -> str | Exception:
        """Return the message for a failure, an empty string for none, or `e` to pass.

        The message is shown in the HUD and kept in errors.txt.
        """
        return e


# Every plugin in the hook files, with the path of the file that defines it.
type Plugins = list[tuple[Path, Plugin]]


def one_line(text: str) -> str:
    """Return `text` on one line, with each run of whitespace collapsed to a space."""
    return " ".join(text.split())


@contextmanager
def labelled(label: str) -> Generator[None]:
    """Add `label` as a note to an exception raised inside, and let it go on."""
    try:
        yield
    except Exception as e:
        e.add_note(label)
        raise


@contextmanager
def labelled_hook(point: str, path: Path) -> Generator[None]:
    """Add a label like `on_cleaned in voice.py:3` to an exception raised inside, and let it go on.

    The line is the last traceback line in the file at `path`, and is left out when there is none.
    """
    try:
        yield
    except Exception as e:
        trace = traceback.extract_tb(e.__traceback__)
        lines = [f.lineno for f in trace if f.filename == str(path)]
        label = f"{point} in {path.name}"
        if lines:
            label += f":{lines[-1]}"
        e.add_note(label)
        raise


def default_message(e: Exception) -> str:
    """Return `label: Type: message` on one line, where the label is the last note on `e`."""
    notes = getattr(e, "__notes__", [])
    label = notes[-1] if notes else ""
    parts = [label, type(e).__name__, str(e).strip()]
    return one_line(": ".join(filter(None, parts)))


def prepend(path: Path, text: str, keep: int) -> None:
    """Put `text` first in the file at `path` as one line, keeping the newest `keep`."""
    new_entry = one_line(text)
    if not new_entry:
        return
    try:
        old_entries = path.read_text(encoding="utf-8").strip().split("\n\n")
    except FileNotFoundError:
        old_entries = []
    entries = [new_entry, *filter(None, old_entries)]
    formatted = "\n\n".join(entries[:keep])
    path.write_text(formatted, encoding="utf-8")


def write_log(text: str) -> None:
    """Add `text` to log.txt."""
    prepend(LOG_FILE, text, 100)


def write_error(message: str) -> None:
    """Add `message` to errors.txt with the time in front. A failed write only goes to stderr."""
    try:
        prepend(ERRORS, f"{datetime.now():%Y-%m-%d %H:%M} {message}", 50)
    except Exception:
        log.exception("errors.txt write failed")


def defined_plugins(names: dict[str, object]) -> list[type[Plugin]]:
    """Return the Plugin subclasses that a file run by `runpy.run_path` defines, in order.

    `names` is the file's globals. A class the file only imported is left out, and a class
    bound to more than one name is returned once.
    """
    classes = [
        value
        for value in names.values()
        if isinstance(value, type)
        and issubclass(value, Plugin)
        and value.__module__ == RUN_PATH_MODULE
    ]
    return list(dict.fromkeys(classes))


def load_plugins(directory: Path) -> Plugins:
    """Return each plugin in every *.py in `directory` with its file's path, in filename order."""
    plugins: Plugins = []
    for path in sorted(directory.glob("*.py")):
        with labelled(f"hook file {path.name}"):
            names = runpy.run_path(str(path), run_name=RUN_PATH_MODULE)
            classes = defined_plugins(names)
            plugins += [(path, plugin_class()) for plugin_class in classes]
    return plugins


def call(point: str, path: Path, hook: Hook, text: str) -> str:
    """Call `hook(text)` and label any failure, including a return that is not a str."""
    with labelled_hook(point, path):
        result = hook(text)
        if not isinstance(result, str):
            raise TypeError(f"{point} returned {type(result).__name__}, not str")
        return result


def call_error(path: Path, hook: ErrorHook, e: Exception) -> str | Exception:
    """Call `hook(e)` and label any failure, including a return that is neither a str nor `e`."""
    with labelled_hook("on_error", path):
        result = hook(e)
        if result is not e and not isinstance(result, str):
            raise TypeError(f"on_error returned {type(result).__name__}, not str or the exception")
        return result


def fire(plugins: Plugins, point: TextPoint, text: str) -> str:
    """Run each plugin's hook for `point` in order while there is text. Each str replaces it."""
    for path, plugin in plugins:
        if not text:
            break
        hook: Hook = getattr(plugin, point)
        text = call(point, path, hook, text)
    return text


def fire_done(plugins: Plugins, text: str) -> None:
    """Run each plugin's on_done hook with `text`. What a hook returns is not used."""
    for path, plugin in plugins:
        call("on_done", path, plugin.on_done, text)


def hook_message(plugins: Plugins, e: Exception) -> str | None:
    """Return the first message a plugin's on_error hook gives for `e`, or None.

    A hook that returns `e` passes it on. One that fails is recorded and skipped.
    """
    for path, plugin in plugins:
        try:
            result = call_error(path, plugin.on_error, e)
        except Exception as failure:
            log.error("on_error hook failed", exc_info=failure)
            write_error(default_message(failure))
            continue
        if isinstance(result, str):
            return one_line(result)
    return None


def report(plugins: Plugins, e: Exception) -> str:
    """Write the message for `e` to errors.txt, unless it is empty, and return it."""
    log.error("dictation failed", exc_info=e)
    default = default_message(e)
    message = hook_message(plugins, e)
    if message is None:
        message = default
    if message:
        write_error(message)
    return message
