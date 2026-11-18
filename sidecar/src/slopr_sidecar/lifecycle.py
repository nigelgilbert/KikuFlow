"""Lifecycle hooks: the on_transcribed, on_cleaned and on_logged functions of plain .py files."""

import logging
import runpy
from collections.abc import Callable, Iterable
from pathlib import Path

from .config import APP_DIR

log = logging.getLogger("uvicorn.error")

POINTS = ("on_transcribed", "on_cleaned", "on_logged")
HOOK_DIRS = (Path(__file__).with_name("hooks"), APP_DIR / "hooks")

type Hooks = dict[str, list[Callable[[str], str | None]]]


def load_hooks(dirs: Iterable[Path]) -> Hooks:
    """The hooks of every *.py in `dirs`, in filename order; a later dir's file replaces a name."""
    files = {path.name: path for d in dirs for path in d.glob("*.py")}
    hooks: Hooks = {point: [] for point in POINTS}
    for name in sorted(files):
        try:
            names = runpy.run_path(str(files[name]))
        except Exception:
            log.exception("hook file %s failed to load", files[name])
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
        if point != "on_logged" and isinstance(new, str):  # on_logged's return is ignored
            text = new
    return text
