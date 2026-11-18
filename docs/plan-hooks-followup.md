# Plan: lifecycle hooks follow-up

Follows `docs/plan-hooks.md` and starts from the code that plan left, after its review and fix
pass. It changes the hook API in four ways that were agreed with the user after the first plan
was under way.

## Goal

```
mic → transcribe → [on_transcribed] → cleanup model → [on_cleaned] → output → [on_output] → log → [on_done]
```

Every hook is plain text in, plain text out:

```python
def on_transcribed(t):
    return t.replace("slopper", "Slopr")
```

One rule covers all four: **a hook fires after its phase, and what it returns is what the next
phase receives.** A hook nobody defines behaves like `lambda t: t`.

| Hook | Fires after | Its return value feeds |
|---|---|---|
| `on_transcribed` | transcribe | the cleanup model |
| `on_cleaned` | cleanup | the output (what the app pastes) |
| `on_output` | output | the log |
| `on_done` | log | nothing; it only observes |

"Output" is the sidecar handing the text to the app. The app normally pastes it, but the
sidecar never learns whether the paste landed, so the phase is not called "paste".

## Why each change

- **Plain text instead of a record.** The first plan passed an `Utterance` with `at`, `raw` and
  `text`. Hooks are simpler to write and to read as `str -> str`, and nothing can be changed
  except by returning. A hook that wants the time calls `datetime.now()`. A hook file that
  wants the raw transcript keeps it in a variable of its own in `on_transcribed`. This
  replaces the first plan's decision to pass the timestamp in.
- **The log is a core phase.** "Open Log…" in the menu must always open a file the app keeps
  up to date. While the log is a hook file, a user file can replace it or turn it off and the
  menu item stops meaning anything.
- **`on_output`.** With the log fixed in core, there still has to be a way to log something
  other than what was output: the raw transcript, a line with a time on it, or nothing for a
  sensitive dictation.
- **`on_logged` becomes `on_done`.** It fires when the dictation is completely finished, and
  the name stays true whatever the last phase is.

## Wording

As in the first plan: a **hook** is one of the functions, a **hook file** is a `.py` file that
defines one or more of them, and the word "plugin" appears nowhere, in code, names, paths,
tests, docs or commit messages. The hook argument is named `t` in every example and doc.

## Design

```python
def on_transcribed(t) -> str | None   # return the text the cleanup model receives
def on_cleaned(t) -> str | None       # return the text that is output
def on_output(t) -> str | None        # return the text that is logged
def on_done(t) -> None                # the dictation is finished
```

- `t` is a plain `str` with no attributes. There is no `Utterance` and no timestamp.
- A hook that returns a `str` replaces the text for the next phase. Returning `None` leaves it
  alone, so a hook that only observes needs no `return`. The return value of `on_done` is
  ignored.
- A hook file defines only the hooks it needs. A hook that is not defined is skipped.
- The rule for empty text is unchanged and applies at every point: once the text is empty,
  nothing further runs. So an `on_output` that returns `""` keeps that dictation out of the
  log, and `on_done` does not fire for it.
- `on_output`, the log and `on_done` all run after the reply has been sent, in that order, on
  the model executor thread. None of them delays the output, and `on_output` cannot change
  what was output: the reply's `clean` is the text `on_cleaned` left.
- The log is written by core: the last 100 texts in
  `~/Library/Application Support/SloprFlow/log.txt`, each flattened to one line, separated by
  one blank line, UTF-8. It has no off switch and no config.
- `on_done` receives the text `on_output` left, which is what was logged.
- Hook files live in one place, `~/Library/Application Support/SloprFlow/hooks/`. There are
  no built-in hook files, so there is no override rule.
- Hooks run one dictation at a time on one thread, so a hook file can keep state between its
  own hooks in module variables. This is how a file gets at the raw transcript:

  ```python
  raw = ""

  def on_transcribed(t):
      global raw
      raw = t

  def on_output(t):
      return raw
  ```

## Items

### 1. Hooks take and return plain text

Remove `Utterance`. Each hook is called with the current text as a `str`, and firing a point
returns the text for the next phase. The server no longer records when the audio arrived.

Acceptance:

- A hook receives a plain `str`. A `str` return replaces the text, `None` leaves it, and hooks
  for one point see the text the previous one left.
- A hook that raises is still logged and skipped, and a point still stops once the text is
  empty.
- `Utterance` and the `at` timestamp are gone from the code, tests and docs.
- A hook file whose `on_transcribed` stores the text in a module variable can read it back in
  a later hook of the same dictation.
- Tests cover the first, second and fourth bullets.

### 2. Move the log into core

The two lines of `sidecar/src/slopr_sidecar/hooks/log.py` become an ordinary function in the
sidecar, called after the reply has been sent and before the last hook fires. Delete
`slopr_sidecar/hooks/` and reduce the loader to the one user directory.

Acceptance:

- Every dictation with non-empty final text is appended to `log.txt` in the existing format:
  last 100, one line each, one blank line between, no timestamps, UTF-8, no leading blank
  entry when the file exists but is empty.
- The log is written with no hook files present, and no hook file can stop it or replace it:
  a user `log.py` is just another hook file.
- The last hook fires after the entry has been written.
- A log write that fails is logged and the last hook still fires.
- The loader reads one directory; the built-in directory and the same-filename rule are gone
  from the code and its tests.
- The test suite never writes the real log: server fixtures point the log path at a temporary
  one.

### 3. Rename `on_logged` to `on_done`

Acceptance:

- `on_done` fires where `on_logged` did. A function named `on_logged` in a hook file is no
  longer called; there is no alias.
- `on_logged` appears nowhere in code, tests or docs.

### 4. Add `on_output`

Acceptance:

- `on_output` fires after the reply has been sent and before the log is written, on the model
  executor thread.
- The text it returns is what is logged; `None` logs the text that was output.
- It cannot change the reply: `clean` is the text `on_cleaned` left.
- Returning `""` writes no log entry and `on_done` does not fire.
- `on_done` receives the text `on_output` left.
- Tests cover each bullet.

### 5. Rework `examples/README.md`

Acceptance:

- It opens with the pipeline diagram and the table from Goal, the four signatures, that an
  undefined hook behaves like `lambda t: t`, the one hooks directory, and that edits take
  effect on "Restart Slopr Flow".
- Every example names the argument `t` and treats it as a plain string.
- The vocabulary and voice examples stay, rewritten for plain text.
- The overriding-the-cleanup example keeps the raw transcript in a module variable from
  `on_transcribed` and decides in `on_cleaned`.
- "Overriding the log" is replaced by `on_output` examples: log the raw transcript instead of
  the output text, put the time from `datetime.now()` on each entry, and keep a dictation out
  of the log.
- An `on_done` example keeps a separate file of the user's own, for instance an unlimited
  archive with timestamps.
- Nothing describes replacing or turning off the built-in log with a file named `log.py`.
- The existing test still loads every `python` block as a hook file.

### 6. Update `README.md` and `sidecar/README.md`

Acceptance:

- Both name the four hooks, say they take and return plain text, and describe the log as
  something the app always keeps, not as a hook file.
- `sidecar/README.md` says that `on_output`, the log and `on_done` run after the response has
  been sent, and no longer mentions built-in hook files or the replace rule.

## Limits to keep

- No change to the app: "Open Log…" already opens `log.txt` and creates it when missing.
- No callback from the app after the paste, and no dependence of the log on the paste landing.
  A paste that fails is when the log is most useful.
- No off switch or config for the log. `on_output` returning `""` is the way to keep an entry
  out.
- Where an acceptance criterion says "docs", it means `README.md`, `sidecar/README.md` and
  `examples/README.md`. Files under `docs/`, this plan included, keep the old names.
- No context passed to hooks beyond the text. If hooks later need more, the sidecar offers
  functions to call; it does not add arguments or attributes.
- No new dependencies.
