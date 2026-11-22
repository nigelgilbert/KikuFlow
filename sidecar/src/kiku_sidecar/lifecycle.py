"""The on_* hooks of plain .py files, the log and errors.txt."""

import logging
import runpy
import traceback
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import APP_DIR

log = logging.getLogger(__name__)

POINTS = ("on_transcribed", "on_cleaned", "on_sent", "on_done")
HOOK_DIR = APP_DIR / "hooks"
LOG_FILE = APP_DIR / "log.txt"
ERRORS = APP_DIR / "errors.txt"

type Hook = Callable[[str], str]
type ErrorHook = Callable[[Exception], str | Exception]
# The hooks of each point with their files: a Hook, or an ErrorHook under "on_error".
type Hooks = dict[str, list[tuple[Path, Callable[[Any], Any]]]]


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


def load_hooks(directory: Path) -> Hooks:
    """Load the hooks of every *.py in `directory`, in filename order."""
    hooks: Hooks = {point: [] for point in (*POINTS, "on_error")}
    for path in sorted(directory.glob("*.py")):
        with labelled(f"hook file {path.name}"):
            names = runpy.run_path(str(path))
        for point in hooks:
            if point in names:
                hooks[point].append((path, names[point]))
    return hooks


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


def fire(hooks: Hooks, point: str, text: str) -> str:
    """Run the hooks for `point` in order while there is text. Each hook's str replaces it."""
    for path, hook in hooks[point]:
        if not text:
            break
        text = call(point, path, hook, text)
    return text


def fire_done(hooks: Hooks, text: str) -> None:
    """Run every on_done hook with `text`. What a hook returns is not used."""
    for path, hook in hooks["on_done"]:
        call("on_done", path, hook, text)


def hook_message(hooks: Hooks, e: Exception) -> str | None:
    """Return the first message an on_error hook gives for `e`, or None.

    A hook that returns `e` passes it on. One that fails is recorded and skipped.
    """
    for path, hook in hooks["on_error"]:
        try:
            result = call_error(path, hook, e)
        except Exception as failure:
            log.error("on_error hook failed", exc_info=failure)
            write_error(default_message(failure))
            continue
        if isinstance(result, str):
            return one_line(result)
    return None


def report(hooks: Hooks, e: Exception) -> str:
    """Write the message for `e` to errors.txt, unless it is empty, and return it."""
    log.error("dictation failed", exc_info=e)
    default = default_message(e)
    message = hook_message(hooks, e)
    if message is None:
        message = default
    if message:
        write_error(message)
    return message
