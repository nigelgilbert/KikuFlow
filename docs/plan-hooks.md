# Plan: pipeline hooks, plugins and the dictation log

## Goal

```
mic → transcribe → [on_transcribed] → cleanup model → [on_cleaned] → paste → log → [on_logged]
```

Three hook points in the sidecar, filled by plugins that are plain Python files. The first
plugin, shipped with the sidecar, writes a plain text log of the last 100 dictations:

```
Example.  Do a thing.  Here is a recording.

Second example.  Do a thing.  This is a second record.

Third example.  Do a thing.  This is a third recording.
```

The code should stay small and read as plain Python: no registry, no decorators, no plugin
framework. Today the whole pipeline is `run()` in `sidecar/src/slopr_sidecar/server.py`.

## Design, already agreed with the user

One record flows through every hook:

```python
@dataclass
class Utterance:
    at: datetime   # when the audio arrived, local time with its zone
    raw: str       # straight from the STT, never changes
    text: str      # what will be pasted; hooks replace this
```

```python
def on_transcribed(u) -> str | None   # after the STT, before the cleanup model
def on_cleaned(u) -> str | None       # after the cleanup stage, before the reply (paste)
def on_logged(u) -> None              # after the reply has gone to the app
```

- A hook that returns a `str` replaces `u.text`. Returning `None` leaves it alone. The return
  value of `on_logged` is ignored.
- A plugin is one `.py` file. Its hooks are the top-level functions with those three names.
  Nothing is imported or registered by the plugin.
- Built-in plugins live in `sidecar/src/slopr_sidecar/plugins/`. User plugins live in
  `~/Library/Application Support/SloprFlow/plugins/`. A user file with the same filename as a
  built-in replaces it, so an empty user `log.py` turns the log off.
- Plugins load in filename order over the merged set, and the hooks for one point run in that
  order, each seeing the text the previous one left.
- A hook that raises is logged with its traceback and skipped; the dictation still completes.
  A plugin file that fails to import is logged and skipped; the models still load.
- Core writes no log. The "log" stage is the hand-off of the finished record to `on_logged`,
  and `plugins/log.py` is the whole logging implementation.
- `on_logged` fires from the sidecar after the reply is sent. The app does not call back.

## Items

### 1. Utterance and the plugin loader

New module `sidecar/src/slopr_sidecar/hooks.py` holding `Utterance`, a loader and a `fire`
function (names are yours to choose, keep them short).

Acceptance:

- The loader takes the directories to read (built-in first, then user), imports every `*.py`
  by path, and returns the hooks per point in filename order. A missing directory is fine.
- A user file with a built-in's filename replaces the built-in; the built-in is not imported.
- A file that raises on import is logged and skipped, and the other plugins still load.
- Firing a point calls its hooks in order; a `str` return replaces `u.text`, `None` does not,
  and a hook that raises is logged and skipped while later hooks still run.
- `u.raw` is never changed by firing.
- Tests cover each bullet, using `tmp_path` directories.

### 2. Run the hooks in the pipeline

Change `server.py` so `run()` builds an `Utterance` and fires the three points. Plugins are
loaded in `load_models`, next to the models, so `/reload` re-reads them.

Acceptance:

- `on_transcribed` fires after the STT. The cleanup model receives `u.text` as the hook left
  it, and `is_plausible` compares against that same text.
- `on_cleaned` fires after the cleanup stage, also when cleanup is off by query or config.
- The pipeline stops as soon as the text is empty: an empty transcription fires no hooks, and
  a hook that returns `""` means nothing is cleaned, pasted or logged after it.
- `on_logged` fires once per dictation with non-empty final text, after the reply has been
  sent, on the model executor thread so hooks never run concurrently. It does not delay the
  reply.
- The `/transcribe` reply keeps its shape: `raw` is the STT output, `clean` is the final
  `u.text`, `timings` keeps its two keys.
- A plugin load failure does not set `/health`'s `error`.
- The test suite never imports the user's real plugins and never writes the real log: the
  server fixtures point the plugin directories at temporary ones.
- Existing server tests still pass. New tests cover each bullet.

### 3. The built-in log plugin

`sidecar/src/slopr_sidecar/plugins/log.py`, as close to this as correctness allows:

```python
LOG = APP_DIR / "log.txt"

def on_logged(u):
    old = LOG.read_text().split("\n\n") if LOG.exists() else []
    LOG.write_text("\n\n".join([*filter(None, old), " ".join(u.text.split())][-100:]))
```

Acceptance:

- After three dictations the file is the three texts separated by one blank line, with no
  timestamps, in the format shown under Goal.
- After 101 dictations the file holds the last 100.
- A multi-paragraph text is flattened to one line, so a blank line always separates entries.
- An empty existing `log.txt` (the menu item creates one) produces no leading blank entry.
- Text is read and written as UTF-8.
- The plugin is in the built wheel: bootstrap installs with `--no-editable`, so check
  `uv build --wheel` output contains `slopr_sidecar/plugins/log.py`.
- Tests cover the first five bullets against a temporary path.

### 4. "Open Log…" in the menu

In `app/Sources/SloprFlow/App.swift`, add "Open Log…" directly under "Open Config…". It
opens `~/Library/Application Support/SloprFlow/log.txt`, creating it empty if missing, with
the same TextEdit fallback as `Config.open()`. Share the opening code in `Config.swift`
instead of copying it.

Acceptance:

- The item appears under "Open Config…" and opens the log file as described.
- `Config.open()` still creates the config with the defaults.
- `app/test.sh` passes.

### 5. `examples/README.md`

A new top-level `examples/README.md` showing how to write and override plugins, for the
scenarios the user named. Each example is a complete plugin file in a `python` fenced block,
with the filename to save it under and one or two sentences on what it does.

- Vocabulary: an `on_transcribed` that corrects words the STT mishears, from a small dict,
  case-insensitively.
- Voice: an `on_cleaned` that changes the style of the text, with a dependency-free example
  (for instance a casual chat voice). Say in prose that a heavier voice can load an `mlx_lm`
  model at import time and call it in `on_cleaned`, since plugins run inside the sidecar.
- Overriding the cleanup result: an `on_cleaned` that uses `u.raw` to decide.
- Overriding the log: a user `log.py` that replaces the built-in, for instance with timestamps
  from `u.at` or a different limit, and the empty `log.py` that turns the log off.

Open with the pipeline diagram, the `Utterance` fields, the three signatures, where plugins
live, the override rule, and that edits take effect on "Restart Slopr Flow".

Acceptance:

- Every `python` block is a working plugin: a sidecar test extracts each block from
  `examples/README.md`, loads it through the loader and checks it defines at least one hook.
- The vocabulary and voice examples match what the loader and `fire` actually do.

### 6. Update the existing docs

- `README.md`: a short section on the log and the menu item, and on plugins, pointing to
  `examples/README.md`.
- `sidecar/README.md`: the hook points in the `/transcribe` section, including that
  `on_logged` runs after the reply.

Acceptance: both files describe the behavior as implemented, in the style of the text around
them.

## Limits to keep

- Vocabulary here means correcting text after the STT. Do not add prompt injection into the
  STT or the cleanup prompt; the cleanup models are trained on a frozen prompt.
- No fourth hook point, no plugin config, no hot reload beyond `/reload` and app restart.
- No new dependencies.
