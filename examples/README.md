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

Each hook gets the text as a plain string `t`, except `on_error`, the one hook that gets the
exception `e` and not the text:

```
def on_transcribed(t) -> str | None   # return the text the cleanup model receives
def on_cleaned(t) -> str | None       # return the text that is output
def on_output(t) -> str | None        # return the text that is logged
def on_done(t) -> None                # the dictation is finished
def on_error(e) -> str | None         # return the message for a failure
```

A hook that returns a string replaces the text; returning `None` leaves it alone, so a hook that
only looks needs no `return`. A hook you don't define behaves like `lambda t: t`. `on_cleaned`
also fires when cleanup is off. Once the text is empty, nothing further runs: `""` from
`on_transcribed` or `on_cleaned` means nothing is pasted or logged, and from `on_output` that the
dictation stays out of the log and `on_done` does not fire.

"Output" is the sidecar handing the text to the app, which pastes it. `on_output`, the log and
`on_done` run after that, so they don't delay the paste, but a slow one holds up the next
dictation. `on_output` cannot change what is pasted.

A failure is loud. When speech recognition, the cleanup model, a hook or the log write raises,
nothing after it runs, and the message, such as `on_cleaned in voice.py:3: KeyError: 'x'`, goes
into `~/Library/Application Support/SloprFlow/errors.txt` ("Open Errors…" in the menu), which
keeps the last 50 with the time in front. Before the reply (speech recognition,
`on_transcribed`, the cleanup model, `on_cleaned`) nothing is pasted and the HUD shows the
message. After it (`on_output`, the log, `on_done`) the text is already pasted and the rest is
skipped: a failing `on_output` means no log entry and no `on_done`. A hook file that fails to
import stops the models loading, and the menu shows the warning triangle with
`hook file voice.py: …`. The full traceback goes to the sidecar's stderr; to see it, quit Slopr
Flow and start its binary from Terminal, for a build from this repo
`"app/build/Slopr Flow.app/Contents/MacOS/SloprFlow"`. See
[When something fails](#when-something-fails) for keeping a dictation and choosing the message.

Hook files live in one place, `~/Library/Application Support/SloprFlow/hooks/`, a folder you
create (`mkdir -p ~/Library/Application\ Support/SloprFlow/hooks`). They load in filename order,
and the hooks for one point run in that order, each seeing the text the previous one left. The
app sends one dictation at a time, so a hook file can keep state between its own hooks in module
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
that sort after it, like `voice.py`, still run on its result. `vocabulary.py` also sorts after
it, so the transcript it keeps, and pastes, does not have the vocabulary fixes.

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
    return f"{datetime.now():%H:%M} {t}"
```

`private.py` keeps a dictation that starts with "private" out of the log. It is still pasted.

```python
import re


def on_output(t):
    if re.match(r"private\b", t, re.IGNORECASE):
        return ""
```

## Your own archive

`on_done` fires once the log entry has been written and gets the text that was logged.
`archive.py` keeps every logged dictation, with the date and time, in a file of your own that
never drops old entries.

```python
from datetime import datetime
from pathlib import Path

ARCHIVE = Path.home() / "Documents/Dictations.txt"


def on_done(t):
    with ARCHIVE.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M}  {' '.join(t.split())}\n")
```

## When something fails

A hook that calls something that can fail, like a web API, catches its own errors and returns
`None`, so the text it was given carries on. This is the way to keep a dictation when a hook's
own call fails. `polish.py` sends the cleaned text to a service of yours and keeps the cleaned
text when the service doesn't answer:

```python
import json
import urllib.request

URL = "http://127.0.0.1:8080/polish"


def on_cleaned(t):
    request = urllib.request.Request(URL, json.dumps({"text": t}).encode())
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)["text"]
    except OSError:
        return None
```

`on_error(e)` decides what a failure says. `e` is the exception itself, with its own type, so
`isinstance` works. The `on_error` hooks run in filename order, and the first one that returns
a string decides what the HUD shows and `errors.txt` gets; the rest don't run. `""` means
nothing is shown or written. `None`, or no `on_error` at all, gives the default message. An
`on_error` that raises is skipped, and its own failure goes into `errors.txt`.

`offline.py` keeps a dropped connection out of `errors.txt`, say from an `on_done` hook that
uploads each dictation to an archive of yours. It sees every failure, so a `ConnectionError`
before the reply is silent too: nothing is pasted and the HUD shows nothing.

```python
def on_error(e):
    if isinstance(e, ConnectionError):
        return ""
```
