# Plan: loud errors, on_error and errors.txt

Starts from `feature/cleanup-prompts` after the merge of main (#2 and #4). It answers the PR #3
review item "a cleanup exception loses the whole dictation". The agreed answer is not to catch
and carry on quietly. Instead, every failure is loud by default, and the user can handle it in
plain Python.

## Rules

- **Exceptions propagate.** Our code no longer catches a hook's exception and carries on. A
  failure in the speech recognition model, the cleanup model, a hook or the log write stops what
  is left of the dictation.
- **Hook signatures stay `on_x(t)`.** Simple hooks need no `try/except`. A hook that wants to
  fall back catches its own errors, for example around an API call, and returns `None`.
- **`on_error(e)` is the one hook that doesn't take text.** It gets the exception itself.
- **`errors.txt` is core, like `log.txt`.** The app always keeps it, and `on_error` decides what
  each entry says, as `on_output` does for the log.

```
error → label it → [on_error] → errors.txt, and the HUD warning if it came before the reply
```

## The label

Before anything sees the exception, the core calls `e.add_note(label)`. `e` keeps its own type,
so `isinstance` checks work, and the label also shows in the traceback. The labels are:

| Failure | Label |
|---|---|
| a hook | `on_cleaned in voice.py:3`: the point, the hook file's name, and the line of the last traceback frame inside that file |
| speech recognition | `speech recognition` |
| cleanup model | `cleanup model` |
| log write | `log write` |

When no traceback frame is inside the hook file (the hook is a function imported from another
module), the label has no line: `on_cleaned in voice.py`.

The **default message** is `f"{label}: {type(e).__name__}: {e}"`, for example
`on_cleaned in voice.py:3: KeyError: 'x'`. An exception with an empty message gives
`label: TimeoutError`, without a trailing colon. The message is folded onto one line
(`" ".join(text.split())`), and so is a string an `on_error` hook returns. The full traceback
still goes to stderr (`log.exception`).

## on_error(e)

```python
def on_error(e) -> str | None
```

- `on_error` hooks run in filename order, each with the same `e`. **The first one that returns
  a string decides** what is shown and written, and the rest don't run. `""` means nothing is
  shown or written. When no hook returns a string, or there is no `on_error`, the default
  message is used.
- A hook that raises is skipped, with its traceback on stderr, and the next hook runs. Its own
  failure also goes into `errors.txt` under the default message `on_error in <file>:<line>: …`,
  and that entry does not go through `on_error` again.
- `on_error` is not one of the text `POINTS`. It is loaded beside them, so the type of `Hooks`
  changes to hold it.

## Where the message goes

- **Before the reply** (speech recognition, `on_transcribed`, cleanup model, `on_cleaned`):
  `/transcribe` returns `500` with the message as `detail`, after it has been written to
  `errors.txt`. Nothing is pasted and nothing goes on the clipboard. If `on_error` returned
  `""`, the reply is still `500`, but `detail` is `""`. The `HTTPException`s `run()` already
  raises, such as the `503` while models load, pass through untouched: they are not labelled,
  not given to `on_error` and not written.
- **After the reply** (`on_output`, the log write, `on_done`): the message goes only to
  `errors.txt` and stderr. Phases after the failure don't run, so a failing `on_output` means no
  log entry and no `on_done`.
- **Load-time failures go to `/health` only**, never to `on_error` or `errors.txt`. A hook file
  that fails to import fails `load_models`, and `/health`'s `error` is the default message with
  the label `hook file voice.py`. The menu shows the warning triangle, the same as for a broken
  config. Model load failures are unchanged.
- **Hooks load before the models**, so a broken hook file fails in milliseconds and not after
  the models have loaded.

## errors.txt

- `~/Library/Application Support/SloprFlow/errors.txt`. Each entry is one line, and the file
  keeps the last 50, in the same format and with the same code shape as `write_log`. Share a
  helper if that keeps both smaller.
- The core puts the time in front of each entry when it writes it:
  `2026-11-18 14:02 on_cleaned in voice.py:3: KeyError: 'x'`. The time is only in the file,
  never in the `detail` the HUD shows.
- If writing `errors.txt` itself fails, the failure goes to stderr only.

## App

- When `/transcribe` fails with a `detail` from the sidecar, show the detail as it is with
  `render(.warning(detail))`, without the "Couldn't transcribe:" prefix. If `detail` is `""`,
  render `.hidden`. Errors that don't come from the sidecar, such as network errors or a sidecar
  reply without a `detail`, keep the prefix.
- Add an "Open Errors…" menu item after "Open Log…", using the same `Config.open` helper, with
  `Config.errors` beside `Config.log`.

## Docs

- `examples/README.md`:
  - Replace the "A hook that raises … is skipped" paragraph with the new rules.
  - Add `on_error` to the hook list, as the one hook that gets the exception and not the text.
  - Add a `try/except` fallback example for an `on_cleaned` hook that calls an API, and say
    this is the way to keep a dictation when a hook's own call fails.
  - Add an `on_error` example for a failure after the reply: return `""` for a
    `ConnectionError`, so a failed upload in an `on_done` archive hook is not recorded. No
    example uses `e.__notes__`.
- Top `README.md`: "Open Errors…" and `errors.txt` next to the Log section, plus `on_error` in
  the hooks paragraph.
- `sidecar/README.md`: in `/transcribe`, the `500` with its `detail`; in the hooks paragraph,
  propagation, `on_error` and `errors.txt`; and the import failure as a `/health` error.
- Keep the wording conventions: "hook" and "hook file", never "plugin".

## Tests

- A hook that raises before the reply: the reply is `500`, `detail` is the labelled message
  including `voice.py:<line>`, nothing later runs, and the entry is in `errors.txt`.
- Speech recognition and the cleanup model raising: same, with their labels.
- After the reply: `on_output`, the log write and `on_done` raising each write `errors.txt`, and
  the phases after them don't run.
- `on_error`:
  - first string wins;
  - `None` falls through to the default;
  - `""` suppresses both the detail and the entry;
  - a raising `on_error` is skipped and recorded;
  - `e` keeps its type and carries the note.
- A hook file that fails to import: the `/health` error carries the label, nothing is written
  to `errors.txt`, and the models were not loaded first.
- The `503` while models load is not labelled, written or given to `on_error`.
- The label without a line, the message without a trailing colon, and a multi-line exception
  message folded onto one line in `detail`.
- `errors.txt`: one line per entry, the time in front, keeps the last 50.
- The existing tests that assert a raising hook is skipped change to the new behaviour.
- `uv run pytest -q && uv run ruff check . && uv run pyright` and `app/test.sh` pass.

## Out of scope

- Any new endpoint or other way to bring errors after the reply to the app.
- Passing tracebacks to the HUD.
- The PR #3 review's item 2, the signing check in `bundle.sh`, which we'll discuss separately.
