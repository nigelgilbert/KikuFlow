"""The on_transcribed, on_cleaned and on_done hooks of plain .py files, and the log."""

import logging
import runpy
from collections.abc import Callable
from pathlib import Path

from .config import APP_DIR

log = logging.getLogger("uvicorn.error")

POINTS = ("on_transcribed", "on_cleaned", "on_done")
HOOK_DIR = APP_DIR / "hooks"
LOG = APP_DIR / "log.txt"

type Hooks = dict[str, list[Callable[[str], str | None]]]


def load_hooks(directory: Path) -> Hooks:
    """The hooks of every *.py in `directory`, in filename order."""
    hooks: Hooks = {point: [] for point in POINTS}
    for path in sorted(directory.glob("*.py")):
        try:
            names = runpy.run_path(str(path))
        except Exception:
            log.exception("hook file %s failed to load", path)
            continue
        for point in POINTS:
            if point in names:
                hooks[point].append(names[point])
    return hooks


def fire(hooks: Hooks, point: str, text: str) -> str:
    """Run the hooks for `point` in order while there is text; a returned str replaces it."""
    for hook in hooks[point]:
        if not text:
            break
        try:
            new = hook(text)
        except Exception:
            log.exception("%s hook failed", point)
            continue
        if point != "on_done" and isinstance(new, str):  # on_done's return is ignored
            text = new
    return text


def write_log(text: str) -> None:
    """Append `text` to the log as one line, keeping the last 100."""
    old = LOG.read_text("utf-8").strip().split("\n\n") if LOG.exists() else []
    LOG.write_text("\n\n".join([*filter(None, old), " ".join(text.split())][-100:]), "utf-8")
