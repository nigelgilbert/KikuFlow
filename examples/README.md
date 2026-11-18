# Lifecycle hooks

Slopr Flow runs your Python at three points of every dictation:

```
mic → transcribe → [on_transcribed] → cleanup model → [on_cleaned] → paste → log → [on_done]
```

A **hook** is a function named after one of those points. A **hook file** is a `.py` file that
defines one or more of them, and nothing else is needed: no imports, no registration. Each hook
gets the text as a plain string `t`:

```
def on_transcribed(t) -> str | None   # after speech recognition, before the cleanup model
def on_cleaned(t) -> str | None       # after the cleanup stage, also when cleanup is off
def on_done(t) -> None                # after the text has been sent to be pasted
```

A hook that returns a string replaces the text; returning `None` leaves it alone. Returning `""`
stops the dictation: nothing is cleaned, pasted or logged after it. A hook that raises, or a hook
file that fails to import, is skipped with its traceback on the sidecar's stderr; the dictation
still completes. To see that output, quit Slopr Flow and start its binary from Terminal, for a
build from this repo `"app/build/Slopr Flow.app/Contents/MacOS/SloprFlow"`.

Put your hook files in `~/Library/Application Support/SloprFlow/hooks/`, a folder you create
(`mkdir -p ~/Library/Application\ Support/SloprFlow/hooks`). Hook files load in filename
order, and the hooks for one point run in that order, each seeing the text the previous one
left. Hook files are read when the sidecar loads its models, so after an edit choose "Restart
Slopr Flow" in the menu.

## Vocabulary

`vocabulary.py` fixes words that speech recognition gets wrong, whatever their case, before the
cleanup model sees them.

```python
import re

WORDS = {"slopper": "Slopr", "jason": "JSON", "mac os": "macOS"}  # keys in lower case
PATTERN = re.compile(r"\b(" + "|".join(map(re.escape, WORDS)) + r")\b", re.IGNORECASE)


def on_transcribed(t):
    return PATTERN.sub(lambda m: WORDS[m[0].lower()], t)
```

## Voice

`voice.py` makes the cleaned text read like a chat message: no capital at the start and no full
stop at the end.

```python
def on_cleaned(t):
    t = t.removesuffix(".")
    return t[:1].lower() + t[1:]
```

Hooks run inside the sidecar, so a heavier voice can load an `mlx_lm` model at import time and
call it with `t` in `on_cleaned`.

## Overriding the cleanup

`verbatim.py` pastes what you said, word for word, when you start with "verbatim". It keeps
the transcript in a variable of its own in `on_transcribed` and decides in `on_cleaned`. Hook
files that sort after it, like `voice.py`, still run on its result.

```python
raw = ""


def on_transcribed(t):
    global raw
    raw = t


def on_cleaned(t):
    first, _, rest = raw.partition(" ")
    if first.strip(",.").lower() == "verbatim":
        return rest
```

## Your own log

The app keeps the last 100 dictations in `~/Library/Application Support/SloprFlow/log.txt`
("Open Log…" in the menu). `archive.py` also keeps every one, with the time, in `archive.txt`
next to it.

```python
from datetime import datetime

from slopr_sidecar.config import APP_DIR


def on_done(t):
    with (APP_DIR / "archive.txt").open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M}  {' '.join(t.split())}\n")
```
