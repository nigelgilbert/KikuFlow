"""Lifecycle hooks: the on_transcribed, on_cleaned and on_logged functions of plain .py files."""

import logging
import runpy
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import APP_DIR

log = logging.getLogger("uvicorn.error")

POINTS = ("on_transcribed", "on_cleaned", "on_logged")
HOOK_DIRS = (Path(__file__).with_name("hooks"), APP_DIR / "hooks")


@dataclass
class Utterance:
    at: datetime  # when the audio arrived, local time with its zone
    raw: str  # straight from the STT, never changes
    text: str  # what will be pasted; hooks replace this


type Hooks = dict[str, list[Callable[[Utterance], str | None]]]


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


def fire(hooks: Hooks, point: str, u: Utterance) -> None:
    """Run the hooks for `point` in order while there is text; a returned str replaces it."""
    for hook in hooks[point]:
        if not u.text:
            return
        try:
            text = hook(u)
        except Exception:
            log.exception("%s hook failed", point)
            continue
        if isinstance(text, str):
            u.text = text
