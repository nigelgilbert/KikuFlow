# Plan: hook refinement

Starts from `feature/cleanup-prompts`. It tightens the hooks that are already there: one clearer
name, cleanup that is always on, one mistake that becomes loud, and much shorter docs. Nothing
needs to stay compatible with existing hook files or configs.

## Rules

- **`on_output` becomes `on_sent`.** The phase it follows is called "send", not "output".
- **Cleanup is always on.** There is no config key, menu item or query parameter that turns it
  off.
- **A wrong return type is loud.** A hook returns `str` or `None`; anything else raises.
- **`on_error(e)` keeps its signature and rules.** The return type check is the only change to
  it.

```
mic → transcribe → [on_transcribed] → cleanup model → [on_cleaned] → send → [on_sent] → log → [on_done]
```

## on_sent

- Rename the point everywhere: `POINTS`, the call in `after_reply`, docstrings, comments, tests
  and docs. Its behaviour is unchanged: it fires once the reply has been sent, and the log gets
  what it returns.
- No alias. An `on_output` left in a hook file is ignored, like any other name that is not a
  hook.

## Cleanup always on

Sidecar:

- Remove `cleanup_enabled` from `Config` and `load_config`. A `[cleanup] enabled` key left in an
  old `config.toml` is ignored, like any other unknown key.
- `load_models` always loads the cleaner, and `Models.clean` is a `Cleaner`, never `None`.
- Remove the `cleanup` parameter from `/transcribe`, `run` and `process`. The cleanup model runs
  whenever the text is not empty after `on_transcribed`.
- `/health` keeps `cleanup_model`, which is now never null when `ready` is true.
- Unchanged: the safety check can still reject the model's output, and `on_cleaned` then gets
  the text `on_transcribed` left.

App:

- Remove the "Clean Up Text" menu item, `toggleCleanup` and the `cleanup` user default.
- `Sidecar.transcribe` takes only the samples and sends no query.
- Remove `cleanupLoaded` and the `cleanupModel` field of `Health`.
- Remove `enabled = true` from `Config.defaults`.

## Return types

- In `fire`, a hook's return value that is neither `str` nor `None` raises
  `TypeError("on_cleaned returned dict, not str or None")`, labelled like any hook failure. The
  raise is in the core, so the label has no line: `on_cleaned in voice.py`.
- It goes down the normal failure path: before the reply a `500` and the HUD, after it
  `errors.txt` only.
- `on_done` is checked the same way. It may return a string, and the string does nothing.
- `on_error` is checked too. A wrong type from it is handled like an `on_error` hook that
  raised: it is skipped, the next one runs, and
  `on_error in offline.py: TypeError: on_error returned dict, not str or None` goes into
  `errors.txt`.

## Docs

`examples/README.md`: replace everything above the first example with this and nothing more.

````markdown
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

Return a string to replace the value, nothing to leave it, `""` to stop there.

Put hook files in `~/Library/Application Support/SloprFlow/hooks/`. They run in filename order.
Choose "Restart Slopr Flow" after an edit.

A hook that raises stops the dictation, and the message goes to the HUD and `errors.txt`.
````

- The signature block keeps its untagged fence: `test_examples.py` loads every `python` block as
  a hook file.
- Keep all nine examples, with `on_output` renamed in `raw_log.py`, `timed_log.py` and
  `private.py`, and one or two sentences of introduction each.
- In "When something fails", cut the paragraph that explains `on_error`'s rules. Keep the
  `polish.py` and `offline.py` examples with their introductions.
- These are deliberately not documented: that a slow `on_sent` or `on_done` holds up the next
  dictation, how to see the full traceback, and that a hook file that fails to import stops the
  models loading.

Top `README.md`:

- Shrink "Lifecycle hooks" to two sentences and the link to `examples/README.md`.
- Remove `enabled = true` from the config block and the "Clean Up Text" sentence.
- Rename `on_output` in the Log section.

`sidecar/README.md`:

- `POST /transcribe` without the `cleanup` query, and without "when cleanup is off" in the
  `clean` and hooks paragraphs.
- Remove `enabled` from the config block and the "`cleanup_model` is null" line under `/health`.
- Rename `on_output`, and add the `TypeError` for a wrong return type.

## Tests

- Rename `on_output` in the existing tests; they otherwise pass unchanged.
- Remove the tests for `?cleanup=false` and `cleanup_enabled = False`, including
  `test_on_cleaned_fires_with_cleanup_off`. The config type test that uses `enabled` moves to
  `safety_check`.
- A leftover `[cleanup] enabled = false` in the config is ignored and cleanup still runs.
- A hook returning a non-string before the reply: `500`, `detail` is
  `on_cleaned in a.py: TypeError: on_cleaned returned dict, not str or None`, nothing later runs.
- The same from `on_sent` and from `on_done`: written to `errors.txt`, and after `on_sent`
  there is no log entry.
- `on_done` returning a string: no error, and the log entry is unchanged.
- An `on_error` returning a non-string: it is skipped and recorded, the next `on_error` still
  decides the message, and without one the default message is used.
- `test_examples.py` still finds nine examples.
- `uv run pytest -q && uv run ruff check . && uv run pyright` and `app/test.sh` pass.

## Out of scope

- Any other change to `on_error`.
- Failing the load on a misspelled hook name. A name that is not a hook stays ignored.
- Giving hooks more than the text, such as the raw transcript or the frontmost app.
- Keeping the dictation when a failure comes before the reply, for example on the clipboard.
