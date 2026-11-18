# Lifecycle hooks

Slopr Flow runs your Python at four points of every dictation:

```
mic → transcribe → [on_transcribed] → cleanup model → [on_cleaned] → output → [on_output] → log → [on_done]
```

A **hook** is a function named after one of those points. A **hook file** is a `.py` file that
defines one or more of them, and nothing else is needed: no imports, no registration. A hook
fires after its phase, and what it returns is what the next phase receives:

| Hook | Fires after | Its return value feeds |
|---|---|---|
| `on_transcribed` | transcribe | the cleanup model |
| `on_cleaned` | cleanup | the output (what the app pastes) |
| `on_output` | output | the log |
| `on_done` | log | nothing; it only observes |

Each hook gets the text as a plain string `t`:

```
def on_transcribed(t) -> str | None   # return the text the cleanup model receives
def on_cleaned(t) -> str | None       # return the text that is output
def on_output(t) -> str | None        # return the text that is logged
def on_done(t) -> None                # the dictation is finished
```

A hook that returns a string replaces the text; returning `None` leaves it alone, so a hook that
only looks needs no `return`. A hook you don't define behaves like `lambda t: t`. `on_cleaned`
also fires when cleanup is off. Once the text is empty, nothing further runs: `""` from
`on_transcribed` or `on_cleaned` means nothing is pasted or logged, and from `on_output` that the
dictation stays out of the log and `on_done` does not fire.

"Output" is the sidecar handing the text to the app, which pastes it. `on_output`, the log and
`on_done` run after that, so they don't delay the paste, and `on_output` cannot change what is
pasted.

A hook that raises, or a hook file that fails to import, is skipped with its traceback on the
sidecar's stderr; the dictation still completes. To see that output, quit Slopr Flow and start
its binary from Terminal, for a build from this repo
`"app/build/Slopr Flow.app/Contents/MacOS/SloprFlow"`.

Hook files live in one place, `~/Library/Application Support/SloprFlow/hooks/`, a folder you
create (`mkdir -p ~/Library/Application\ Support/SloprFlow/hooks`). They load in filename order,
and the hooks for one point run in that order, each seeing the text the previous one left. Hooks
run one dictation at a time, so a hook file can keep state between its own hooks in module
variables. Hook files are read when the sidecar loads its models, so after an edit choose
"Restart Slopr Flow" in the menu.

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

`verbatim.py` pastes what you said, word for word, when you start with "verbatim". It keeps the
transcript in a variable of its own in `on_transcribed` and decides in `on_cleaned`. Hook files
that sort after it, like `voice.py`, still run on its result.

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

## What goes in the log

The app always keeps your last 100 dictations in
`~/Library/Application Support/SloprFlow/log.txt` ("Open Log…" in the menu), one line each. An
entry is the text that was output, unless an `on_output` hook returns something else.

`raw_log.py` logs what you said instead of the cleaned text:

```python
raw = ""


def on_transcribed(t):
    global raw
    raw = t


def on_output(t):
    return raw
```

`timed_log.py` puts the time on each entry. It sorts after `raw_log.py`, so with both the log
holds the time and what you said.

```python
from datetime import datetime


def on_output(t):
    return f"{datetime.now():%H:%M}  {t}"
```

`private.py` keeps a dictation that starts with "private" out of the log. It is still pasted.

```python
def on_output(t):
    if t.lower().startswith("private"):
        return ""
```

## Your own archive

`on_done` fires once the log entry has been written and gets the text that was logged.
`archive.py` keeps every dictation, with the date and time, in a file of your own that never
drops old entries.

```python
from datetime import datetime
from pathlib import Path

ARCHIVE = Path.home() / "Documents/Dictations.txt"


def on_done(t):
    with ARCHIVE.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M}  {' '.join(t.split())}\n")
```
