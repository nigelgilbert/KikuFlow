# Factory report: feature/cleanup-prompts, run 2

- Work file: `docs/plan-errors.md`
- Branch: `feature/cleanup-prompts`, after the merge of main (#2 and #4)
- Base commit: `06c67c05d570205ca63247a66087fa54438da033`
- Reviews: 1, adversary `sol`

## Pass 0: what landed

| Item | Commit | What landed |
|---|---|---|
| 1. Labels and propagation | `f3e2466` | `fire()` no longer catches. It adds a note such as `on_cleaned in voice.py:3` and re-raises. `labelled()` adds `speech recognition`, `cleanup model` and `log write`. `default_message(e)` builds the one-line message. `Hooks` keeps each hook's file. |
| 2. `on_error(e)` | `569c044` | `report(hooks, e)` runs the `on_error` hooks in filename order. The first string wins, `""` suppresses, and a raising hook is skipped. |
| 3. `errors.txt` | `76551d7` | A shared `append` helper backs `write_log` (100 entries) and `write_error` (50 entries, with the time in front). A failed write goes to stderr only. |
| 4. Server boundary | `5638025` | Failures before the reply give `500` with the message as `detail`. Failures after the reply are reported and stop the later phases. The 503 passes through. Hooks load first, and a broken hook file fails the load. |
| 5. App | `9209d18` | A sidecar `detail` is shown as it is, or the HUD hides when it is empty. "Open Errors…" is in the menu. |
| 6. Docs | `73d1eea` | The three READMEs, with `polish.py` and `offline.py` examples. |
| 7. Tests | with 1–4, and `e501a6a` | Every case in the plan's Tests section. |

Left open by the implementer: the 400 and 503 replies also lose the "Couldn't transcribe:" prefix, since they carry a `detail` too.

## Review 1: trimmed list

Range `06c67c05d570205ca63247a66087fa54438da033..e501a6a1834ee28dc299d42f430daaec83d86af4`.

### Fix

1. **A whitespace-only exception message leaves a trailing colon** (C9)
   - Where: `sidecar/src/slopr_sidecar/lifecycle.py:59`
   - Problem: `RuntimeError("\n")` with the note `cleanup model` gives `'cleanup model: RuntimeError:'`. The plan says no trailing colon.
   - Fix: change `str(e)` to `str(e).strip()` on line 59, and add a test for it in `test_lifecycle.py`.
   - Confidence: medium.

2. **The `offline.py` example doesn't catch what the README's own network code raises** (C2)
   - Where: `examples/README.md:203-210`
   - Problem: the text says the file keeps a dropped connection from an uploading `on_done` hook out of `errors.txt`. With `urllib`, which `polish.py` uses, a refused connection raises `URLError`, not the builtin `ConnectionError`, so the entry is still recorded.
   - Fix (the user's choice): make the example work, with `isinstance(getattr(e, "reason", e), ConnectionError)`, and change the test to raise a `URLError`. Keep the prose and the example minimal.
   - Confidence: medium.

### Nit

3. **An empty 400 `detail` hides the HUD silently** (C1)
   - Where: `sidecar/src/slopr_sidecar/server.py:162`
   - Problem: `decode_audio(b"RIFF")` raises `EOFError` with an empty message, so the reply is a `400` with `detail` `""`, which the app renders as `.hidden`. The app can't reach this today.
   - Fix: `raise HTTPException(400, str(e) or type(e).__name__) from e`.
   - Confidence: medium.

### Wontfix

- C3 `polish.py` catches only `OSError`: a malformed 200 is not "doesn't answer", and failing loudly there fits the plan.
- C4 the prefix is dropped for 400 and 503 too: the plan says a sidecar detail is shown as it is.
- C5 `report()` itself raising: far-fetched, and a guard costs more than the defect.
- C6 a failed log write skips `on_done`: the plan mandates it.
- C7 `add_note` accumulates on a reused exception: the plan requires the note, and only the last one is read.
- C8 two formats for load errors: the plan says model load failures are unchanged.
- C10 no `on_error` row in the README table: the text under the table already names it and gives its signature.
- C11 the test raises a bare `ConnectionRefusedError`: it follows whatever Fix 2 becomes.

### Split

None.

### Counts

11 candidates, 3 kept (2 fix, 1 nit), 8 wontfix. Adversary `sol`, 2 exchanges.
