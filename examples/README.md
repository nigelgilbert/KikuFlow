# Lifecycle hooks

```
mic → transcribe → [on_transcribed] → cleanup model → [on_cleaned] → send → [on_sent] → log → [on_done]
```

```
def on_transcribed(t) -> str | None   # after speech recognition; returns the text to clean up
def on_cleaned(t) -> str | None       # after the cleanup model; returns the text to paste
def on_sent(t) -> str | None          # after the text is sent to be pasted; returns the text to log
def on_done(t) -> None                # after the log entry is written
def on_error(e) -> str | None         # after a failure; returns the message to show and keep
```

A text hook returns a string to replace the text, nothing to leave it, or `""` to stop there.
`on_error` returns the message, nothing for the default one, or `""` for none.

Put hook files in `hooks/` in this repo. They run in filename order.
Choose "Reload Kiku Flow" after an edit.

A hook that raises stops the dictation. The message goes to `errors.txt`, and to the HUD when
nothing has been pasted yet.

## Vocabulary

`vocabulary.py` fixes words that speech recognition gets wrong, whatever their case, before the
cleanup model sees them.

```python
import re

WORDS = {"kiko": "Kiku", "jason": "JSON", "mac os": "macOS"}  # keys in lower case
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

## Overriding the cleanup

`verbatim.py` pastes what you said, word for word, when you start with "verbatim". `vocabulary.py`
sorts after it, so the transcript it pastes does not have the vocabulary fixes.

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

An entry in the log is what `on_sent` returns. `raw_log.py` logs what you said instead of the
cleaned text.

```python
raw = ""


def on_transcribed(t):
    global raw
    raw = t


def on_sent(t):
    return raw
```

`timed_log.py` puts the time on each entry. It sorts after `raw_log.py`, so with both the log
holds the time and what you said.

```python
from datetime import datetime


def on_sent(t):
    return f"{datetime.now():%H:%M} {t}"
```

`private.py` keeps a dictation that starts with "private" out of the log. It is still pasted.

```python
import re


def on_sent(t):
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

A hook that calls something that can fail catches its own errors and returns `None` to keep the
dictation. `polish.py` sends the cleaned text to a service of yours and keeps it when the
service doesn't answer.

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

`offline.py` keeps a failed upload, say from an `on_done` archive hook, out of `errors.txt`.
`urllib` wraps the `ConnectionError` in `e.reason`.

```python
def on_error(e):
    if isinstance(getattr(e, "reason", e), ConnectionError):
        return ""
```
