"""The on_* hooks of plain .py files, the log and errors.txt."""

import logging
import runpy
import traceback
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .config import APP_DIR

log = logging.getLogger(__name__)

POINTS = ("on_transcribed", "on_cleaned", "on_sent", "on_done")
HOOK_DIR = APP_DIR / "hooks"
LOG_FILE = APP_DIR / "log.txt"
ERRORS = APP_DIR / "errors.txt"

type Hook = Callable[..., str]
type Hooks = dict[str, list[tuple[Path, Hook]]]


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


def hook_label(point: str, path: Path, e: Exception) -> str:
    """Return a label like `on_cleaned in voice.py:3`, using the last traceback line in the file."""
    trace = traceback.extract_tb(e.__traceback__)
    lines = [f.lineno for f in trace if f.filename == str(path)]
    label = f"{point} in {path.name}"
    if lines:
        label += f":{lines[-1]}"
    return label


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


def call(point: str, path: Path, hook: Hook, *args: str | Exception) -> str:
    """Call `hook(*args)` and label any failure, including a return that is not a str."""
    try:
        result = hook(*args)
        if not isinstance(result, str):
            raise TypeError(f"{point} returned {type(result).__name__}, not str")
    except Exception as e:
        e.add_note(hook_label(point, path, e))
        raise
    return result


def fire(hooks: Hooks, point: str, text: str) -> str:
    """Pipe `text` through the hooks for `point` in order, while there is text."""
    for path, hook in hooks[point]:
        if not text:
            break
        text = call(point, path, hook, text)
    return text


def fire_error(hooks: Hooks, e: Exception, message: str) -> str:
    """Pipe `message` through the on_error hooks. A failed hook is recorded and skipped."""
    for path, hook in hooks["on_error"]:
        if not message:
            break
        try:
            message = one_line(call("on_error", path, hook, e, message))
        except Exception as failure:
            log.error("on_error hook failed", exc_info=failure)
            write_error(default_message(failure))
    return message


def report(hooks: Hooks, e: Exception) -> str:
    """Write the message for `e` to errors.txt, unless it is empty, and return it."""
    log.error("dictation failed", exc_info=e)
    message = fire_error(hooks, e, default_message(e))
    if message:
        write_error(message)
    return message
