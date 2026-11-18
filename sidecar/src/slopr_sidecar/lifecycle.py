"""The on_* hooks of plain .py files, and the log."""

import logging
import runpy
import traceback
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .config import APP_DIR

log = logging.getLogger("uvicorn.error")

POINTS = ("on_transcribed", "on_cleaned", "on_output", "on_done")
HOOK_DIR = APP_DIR / "hooks"
LOG = APP_DIR / "log.txt"

# Each hook with the file it was loaded from, for its label. on_error takes the exception.
type Hooks = dict[str, list[tuple[Path, Callable[[Any], str | None]]]]


def load_hooks(directory: Path) -> Hooks:
    """The hooks of every *.py in `directory`, in filename order."""
    hooks: Hooks = {point: [] for point in (*POINTS, "on_error")}
    for path in sorted(directory.glob("*.py")):
        try:
            names = runpy.run_path(str(path))
        except Exception:
            log.exception("hook file %s failed to load", path)
            continue
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
    parts = [*getattr(e, "__notes__", [])[-1:], type(e).__name__, str(e)]
    return fold(": ".join(filter(None, parts)))


def fire(hooks: Hooks, point: str, text: str) -> str:
    """Run the hooks for `point` in order while there is text; a returned str replaces it."""
    for path, hook in hooks[point]:
        if not text:
            break
        try:
            new = hook(text)
        except Exception as e:
            e.add_note(hook_label(point, path, e))
            raise
        if point != "on_done" and isinstance(new, str):  # on_done's return is ignored
            text = new
    return text


def report(hooks: Hooks, e: Exception) -> str:
    """The message for `e`: the first str an on_error hook returns, else the default."""
    log.error("dictation failed", exc_info=e)
    for path, hook in hooks["on_error"]:
        try:
            message = hook(e)
        except Exception as failure:
            failure.add_note(hook_label("on_error", path, failure))
            log.error("on_error hook failed", exc_info=failure)
            continue
        if isinstance(message, str):
            return fold(message)
    return default_message(e)


def write_log(text: str) -> None:
    """Append `text` to the log as one line, keeping the last 100."""
    old = LOG.read_text("utf-8").strip().split("\n\n") if LOG.exists() else []
    LOG.write_text("\n\n".join([*filter(None, old), fold(text)][-100:]), "utf-8")
