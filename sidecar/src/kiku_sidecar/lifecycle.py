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

# uvicorn's logger, not __name__, so that errors go to stderr in uvicorn's format.
log = logging.getLogger("uvicorn.error")

POINTS = ("on_transcribed", "on_cleaned", "on_sent", "on_done")
HOOK_DIR = APP_DIR / "hooks"
LOG_FILE = APP_DIR / "log.txt"
ERRORS = APP_DIR / "errors.txt"

# Each hook with the file it was loaded from, for its label. on_error takes the exception.
type Hooks = dict[str, list[tuple[Path, Callable[[Any], str | None]]]]


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


@contextmanager
def labelled(label: str) -> Generator[None]:
    """Add `label` as a note to an exception raised inside, and let it go on."""
    try:
        yield
    except Exception as e:
        e.add_note(label)
        raise


def hook_label(point: str, path: Path, e: Exception) -> str:
    """Return a label like `on_cleaned in voice.py:3`, using the last traceback line in the file."""
    trace = traceback.extract_tb(e.__traceback__) 
    lines = [f.lineno for f in trace if f.filename == str(path)]
    label = f"{point} in {path.name}"
    if lines:
        label += f":{lines[-1]}"
    return label


def one_line(text: str) -> str:
    """Return `text` on one line, with each run of whitespace collapsed to a space."""
    return " ".join(text.split())


def default_message(e: Exception) -> str:
    """Return `label: Type: message` on one line, where the label is the last note on `e`."""
    notes = getattr(e, "__notes__", [])
    label = notes[-1] if notes else ""
    parts = [label, type(e).__name__, str(e).strip()]
    return one_line(": ".join(filter(None, parts)))


def call(point: str, path: Path, hook: Callable[[Any], str | None], arg: Any) -> str | None:
    """Call `hook(arg)` and label any failure, including a return that is not str or None."""
    try:
        new = hook(arg)
        if new is not None and not isinstance(new, str):
            raise TypeError(f"{point} returned {type(new).__name__}, not str or None")
    except Exception as e:
        e.add_note(hook_label(point, path, e))
        raise
    return new


def fire(hooks: Hooks, point: str, text: str) -> str:
    """Run the hooks for `point` in order while there is text; a returned str replaces it."""
    for path, hook in hooks[point]:
        if not text:
            break
        new = call(point, path, hook, text)
        if point != "on_done" and new is not None:  # a str from on_done changes nothing
            text = new
    return text


def report(hooks: Hooks, e: Exception) -> str:
    """Write the message for `e` to errors.txt and return it: the first str an on_error hook
    returns, else the default."""
    log.error("dictation failed", exc_info=e)
    message = default_message(e)
    for path, hook in hooks["on_error"]:
        try:
            new = call("on_error", path, hook, e)
        except Exception as failure:
            log.error("on_error hook failed", exc_info=failure)
            write_error(default_message(failure))
            continue
        if new is not None:
            message = one_line(new)
            break
    if message:
        write_error(message)
    return message


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
    prepend(LOG_FILE, text, 100)


def write_error(message: str) -> None:
    """Add `message` to errors.txt with the time in front; a failed write only goes to stderr."""
    try:
        prepend(ERRORS, f"{datetime.now():%Y-%m-%d %H:%M} {message}", 50)
    except Exception:
        log.exception("errors.txt write failed")
