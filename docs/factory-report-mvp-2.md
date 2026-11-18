# Factory report: lifecycle hooks and the dictation log

- Work file: `docs/plan-hooks.md`
- Branch: `mvp`, base commit `130805e`
- Reviews: 1, adversary `sol`
- Pull request: https://github.com/nigelgilbert/slopr/pull/1

## Work items

| Item | What landed | Commit |
|---|---|---|
| 1. `Utterance` and the hook loader | `sidecar/src/slopr_sidecar/lifecycle.py`: `Utterance`, `HOOK_DIRS`, `load_hooks` and `fire`, about 50 lines. Hook files run with `runpy.run_path`. `fire` stops once the text is empty, which is how the pipeline stops. | `e07ca19` |
| 2. Hooks in the pipeline | `load_models` loads the hooks, so `/reload` re-reads them. `run()` fires `on_transcribed` and `on_cleaned` and returns the `on_logged` call, which the handler runs as a background task on the model executor after the response is sent. | `4b63660` |
| 3. The built-in log hook | `sidecar/src/slopr_sidecar/hooks/log.py`: the plan's two lines with explicit UTF-8. The wheel contains it. | `0cdae4a` |
| 4. "Open Log…" | `Config.openLog()` and a shared private `open(_:creatingWith:)` in `Config.swift`; the menu item sits under "Open Config…". | `c30069f` |
| 5. `examples/README.md` | Four hook files (`vocabulary.py`, `voice.py`, `verbatim.py`, a timestamped `log.py`) and the empty `log.py`. `tests/test_examples.py` loads every `python` block. | `3eaa0b7` |
| 6. Docs | "Log" and "Lifecycle hooks" sections in `README.md`; the hooks in the `/transcribe` section of `sidecar/README.md`. | `d4e693d` |

Not checked by hand: clicking "Open Log…" in the running app, and a dictation with the real
models through the hooks.

## Review 1

Range `130805e..d4e693d`. The reviewer raised 26 candidates. The filter agent kept 10 after
its own read, an independent read from `sol`, and one follow-up exchange on the 7 candidates
where the two differed. Numbers in brackets are the reviewer's.

### Fix

1. **[3] `on_logged` return values are applied, not ignored** (`sidecar/src/slopr_sidecar/lifecycle.py:54`)
   - Problem: the design says the return value of `on_logged` is ignored, but `fire` applies
     it. An `on_logged` that returns a string changes what later `on_logged` hooks see, and one
     that returns `""` stops them.
   - Fix: `if point != "on_logged" and isinstance(text, str):` on line 54. Keep the
     `if not u.text: return` check, which is what stops `on_logged` firing on empty text. Add
     one test in `test_lifecycle.py`.
   - Confidence: high.
2. **[4] The documented `touch …/hooks/log.py` fails on a fresh install** (`examples/README.md:99`, also `:30`, `README.md:95`)
   - Problem: nothing creates `~/Library/Application Support/SloprFlow/hooks/`.
   - Fix, docs only: `mkdir -p` the folder before the `touch`, and say where hook files are
     introduced that the reader creates the folder.
   - Confidence: high.
3. **[9] The docs point hook authors at a stderr they cannot see** (`examples/README.md:26-28`)
   - Problem: a failing hook is "skipped with its traceback on the sidecar's stderr", and a
     Finder-launched app shows that nowhere.
   - Fix, docs only: one sentence on how to see it, for example starting the app binary from
     Terminal. The implementer confirms the sidecar inherits the terminal's stderr first.
   - Confidence: medium. `sol` first said nit, then backed fix.

### Nit

4. **[1] `SystemExit` escapes the hook isolation** (`lifecycle.py:35` and `:51`)
   - Problem: a hook file that calls `sys.exit()` at import escapes `load_models` too, so
     `/health` reports loading forever.
   - Fix: `except (Exception, SystemExit):` in both places.
   - Confidence: medium. `sol` first said fix, then backed nit.
5. **[22] No test that the reply is sent before `on_logged` runs** (`sidecar/tests/test_server.py`)
   - Problem: changing the background task into an awaited call would fail no test.
   - Fix: a raw ASGI test of about 12 lines that records the hook calls when the
     `http.response.body` message is sent.
   - Confidence: low. Split, see below.
6. **[2] "never delays the paste" overclaims** (`sidecar/README.md:66`)
   - Problem: `on_logged` runs on the single model executor, as designed, so a slow one holds
     up the next dictation.
   - Fix, docs only: say it does not delay that reply, and that a slow `on_logged` holds up
     the next dictation.
   - Confidence: medium. `sol` first said fix, then backed nit.
7. **[5] "after the paste" is looser than the other two docs** (`README.md:94`)
   - Fix: "`on_logged` once the text has been sent to be pasted".
   - Confidence: medium. `sol` first said fix, then backed nit.
8. **[11] A trailing newline in `log.txt` leaves a doubled blank line** (`sidecar/src/slopr_sidecar/hooks/log.py:9`)
   - Problem: after a save from an editor that appends a newline, the next entry follows two
     blank lines.
   - Fix: `LOG.read_text("utf-8").strip().split("\n\n")`, and the same in the example at
     `examples/README.md:91`.
   - Confidence: high. `sol` thought no fix earned its place.
9. **[6] `verbatim.py` is not word for word once `voice.py` is installed** (`examples/README.md:68-69`)
   - Fix: one sentence that hook files sorting after it still run on its result.
   - Confidence: high.
10. **[7] The vocabulary example breaks on a key with capitals** (`examples/README.md:44`)
    - Fix: a comment that keys are lower case.
    - Confidence: high.

### Wontfix

- [8] Voice example returns `""` for a lone ".": that is the documented stop rule.
- [10] Hook time inside `cleanup_ms`: nothing reads `timings`, and the two keys are kept.
- [12] Non-atomic log rewrite: a tiny window, and the fix adds lines to a two-line hook.
- [13] Returning to the built-in log trims to 100: that is what "last 100" means.
- [14] A hook can assign `u.raw`: hooks are trusted, and the fix changes the agreed dataclass.
- [15] Dotfiles match `*.py`: the worst case is one logged traceback.
- [16] A non-callable hook name: contrived, and already logged and skipped.
- [17] Case-sensitive filename order: the design says filename order.
- [18] An unreadable hooks folder is silent: contrived for the user's own folder.
- [19] No imports of a neighbouring file: the design says a hook file is one `.py` file.
- [20] The failure log does not name the file: the traceback does.
- [21] A background task is queued on empty text: a no-op.
- [23] No server test of `on_cleaned` returning `""`: the same check is covered by two tests.
- [24] No behaviour tests for the examples: the work file specifies the test that exists.
- [25] `read_text()` without an encoding in a test: not a failure on the supported setup.
- [26] "no imports" against the log example: the sentence says none are needed, which is true.

### Split

- **[22] The reply-before-`on_logged` test.** The filter agent says nit, `sol` says fix.
  - `sol`: "New tests cover each bullet" includes reply ordering, and the existing tests
    would miss moving the call before the response.
  - Filter agent: the untested link is one line relying on Starlette's documented
    background-task contract, and the reviewer's experiment shows the behaviour is right
    today.

Counts: 26 candidates, 10 kept (3 fix, 7 nit), 16 wontfix, 1 split, adversary `sol`,
2 exchanges.

## Fix pass

Pass base `bbd09f0`. The Fix and Nit items went to the implementer, which folded in 9 of the
10 and pushed back on one.

| Item | Result | Commit |
|---|---|---|
| 1 [3] `on_logged` return values | Folded in. `fire` applies a returned string only when the point is not `on_logged`; the empty-text check is kept. New test in `test_lifecycle.py`. | `f14e840` |
| 2 [4] The hooks folder is never created | Folded in, docs only. `examples/README.md` and `README.md` say it is a folder you create, and the turn-off recipe runs `mkdir -p` first. | `0b9c972` |
| 3 [9] Invisible stderr | Folded in, docs only. `examples/README.md` says to quit the app and start its binary from Terminal. Confirmed first that the sidecar inherits the app's stderr: `launch()` sets no `standardError`, and a scratch Swift program showed a `Process` child's stderr reaching the parent's. | `0b9c972` |
| 4 [1] `SystemExit` escapes | Not folded in. See below. | |
| 5 [22] Reply-before-`on_logged` test | Folded in. A raw ASGI test records the hook calls when the response body is sent. It fails when the background task is changed to an awaited call. | `edfd473` |
| 6 [2] "never delays the paste" | Folded in. `sidecar/README.md` says `on_logged` does not delay that reply and that a slow one holds up the next dictation. | `0b9c972` |
| 7 [5] "after the paste" | Folded in. `README.md` says "once the text has been sent to be pasted". | `0b9c972` |
| 8 [11] Trailing newline in `log.txt` | Folded in. `hooks/log.py` strips before splitting, with a test; the log example matches. | `b48d2c9`, `0b9c972` |
| 9 [6] `verbatim.py` and `voice.py` | Folded in. One sentence in `examples/README.md`. | `0b9c972` |
| 10 [7] Vocabulary keys | Folded in. The `WORDS` line carries `# keys in lower case`. | `0b9c972` |

Pushback on item 4: the implementer judged a hook file that calls `sys.exit()` at import to be
as contrived as the non-callable hook name the Wontfix list already accepts ([16]), and not
worth extra code in the loader. The lead accepted that: the item was a nit at medium
confidence, and hook files are the user's own code.

## Open items

- **`SystemExit` in a hook file (item 4).** Left as is. A hook file that calls `sys.exit()`
  at import leaves `/health` reporting loading with no error. The change, if wanted, is
  `except (Exception, SystemExit):` at the two `except` lines in `lifecycle.py`.
- **Not checked by hand.** Clicking "Open Log…" in the running app, and a dictation with the
  real models through the hooks.
- **`docs/plan-hooks-followup.md`.** An untracked follow-up plan appeared in the checkout
  during the run. It is not part of this run and is not committed.

No items were struck by the user.

## Tests

- Sidecar, from `sidecar/`: `uv run pytest -q && uv run ruff check . && uv run pyright` gives
  48 passed, ruff clean, pyright 0 errors (21 tests at the base commit).
- App: `app/test.sh` gives 7 tests passed.
