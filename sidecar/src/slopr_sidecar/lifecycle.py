"""The on_* hooks of plain .py files, the log and errors.txt."""

import logging
import runpy
import traceback
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import APP_DIR

log = logging.getLogger("uvicorn.error")

POINTS = ("on_transcribed", "on_cleaned", "on_sent", "on_done")
HOOK_DIR = APP_DIR / "hooks"
LOG = APP_DIR / "log.txt"
ERRORS = APP_DIR / "errors.txt"

# Each hook with the file it was loaded from, for its label. on_error takes the exception.
type Hooks = dict[str, list[tuple[Path, Callable[[Any], str | None]]]]


def load_hooks(directory: Path) -> Hooks:
    """The hooks of every *.py in `directory`, in filename order."""
    hooks: Hooks = {point: [] for point in (*POINTS, "on_error")}
    for path in sorted(directory.glob("*.py")):
        with labelled(f"hook file {path.name}"):
            names = runpy.run_path(str(path))
        for point in hooks:
            if point in names:
                hooks[point].append((path, names[point]))
    return hooks


@contextmanager
def labelled(label: str) -> Iterator[None]:
    """Add `label` as a note to an exception raised inside, and let it go on."""
    try:
        yield
    except Exception as e:
        e.add_note(label)
        raise


def hook_label(point: str, path: Path, e: BaseException) -> str:
    """`on_cleaned in voice.py:3`, the line being that of the last traceback frame in the file."""
    lines = [f.lineno for f in traceback.extract_tb(e.__traceback__) if f.filename == str(path)]
    return f"{point} in {path.name}" + (f":{lines[-1]}" if lines else "")


def fold(text: str) -> str:
    return " ".join(text.split())


def default_message(e: BaseException) -> str:
    """`label: Type: message` on one line, the label being the last note on `e`."""
    parts = [*getattr(e, "__notes__", [])[-1:], type(e).__name__, str(e).strip()]
    return fold(": ".join(filter(None, parts)))


def call(point: str, path: Path, hook: Callable[[Any], str | None], arg: Any) -> str | None:
    """`hook(arg)`; a failure, or a return that is not str or None, raises labelled."""
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
            message = fold(new)
            break
    if message:
        write_error(message)
    return message


def prepend(path: Path, text: str, keep: int) -> None:
    """Put `text` first in the file at `path` as one line, keeping the first `keep`."""
    if not (text := fold(text)):
        return
    old = path.read_text("utf-8").strip().split("\n\n") if path.exists() else []
    path.write_text("\n\n".join([text, *filter(None, old)][:keep]), "utf-8")


def write_log(text: str) -> None:
    prepend(LOG, text, 100)


def write_error(message: str) -> None:
    """Add `message` to errors.txt with the time in front; a failed write only goes to stderr."""
    try:
        prepend(ERRORS, f"{datetime.now():%Y-%m-%d %H:%M} {message}", 50)
    except Exception:
        log.exception("errors.txt write failed")
