# Factory report: feature/command-renderer, run 1

- Work file: `docs/plan-command-renderer.md`
- Branch: `feature/command-renderer`, in the worktree `slopr-command-renderer`, cut from main at
  `08a2018` (after #8)
- Base commit: `6d7ed71e0eae3b9f31bb4afe84840cd87fa046e5`
- Reviews: 1, adversary `sol`

## Pass 0: what landed

| Item | Commit | What landed |
|---|---|---|
| 1. `[hud] renderer` | `259aba9` | `Config.renderer`, read like `port` and `hotkey`, nil when missing or empty. A `[hud]` section with a commented key in the defaults. |
| 2. `HUDState.line` | `2cff112` | The four lines of the plan's table. The level is clamped and written with two decimals; line breaks in a warning become spaces. |
| 3. `SloprHUD` | `3b198b8` | A second executable target in one file, `app/Sources/SloprHUD/main.swift`, with the panel, the notch placement, the level history and the view. It reads lines on a background thread, ignores unknown ones and exits when its input closes. |
| 4. `Renderer` as a pipe | `be901bb` | `Renderer` is a final class that starts the user's command through `/bin/sh -c`, or `SloprHUD` from beside the app's executable, and writes each state's line. `SIGPIPE` is ignored and the write end is non-blocking. Both fallbacks of the plan are in. |
| 5. Bundle | `a13825b` | `bundle.sh` copies `SloprHUD` into `Contents/MacOS/` and signs it before the bundle. |
| 6. Example and docs | `19885ef` | `examples/hud.py`, and "Your own HUD" and `[hud]` in the top README. |

Two additions the plan did not name, both in item 4: `App` calls `hud.start()` at launch, and
`Renderer` has an `onStop` callback, so the "The HUD renderer stopped" warning goes through
`App.render` and gets the 1.5 s hide.

### What was run and what was only read

The user's own app was running on the machine, so nothing built here was launched as an app.

- Run: `SloprHUD` alone with lines piped in; `Renderer.swift` in a scratch harness with
  `cat >> states.txt`, `exit 1`, a command that does not exist, a killed stand-in for
  `SloprHUD`, and a reader that never reads; `bundle.sh` with a throwaway home, with
  `codesign --verify --deep --strict` passing; `hud.py` with a stand-in `say`.
- Only read: the four app-level points of item 4 (the same pill with no `[hud]` section,
  `cat >> states.txt` beside the real config, `exit 1` in the real app, killing `SloprHUD`
  while the app runs).

## Review 1: trimmed list

Range `6d7ed71e0eae3b9f31bb4afe84840cd87fa046e5..19885ef8eb5bfcc02139d452c98a6734be58dc44`.

The reviewer found every acceptance criterion met at the head commit.

### Fix

1. **The config reader breaks a command that ends in a quote** (C3)
   - Where: `app/Sources/SloprFlow/Config.swift:63`
   - Problem: the reader strips every quote from both ends of a value, so
     `renderer = "say 'done'"` becomes `say 'done`. The shell fails and the user sees only
     "The HUD renderer stopped".
   - Fix: strip one matching pair of quotes only, and add a test with `"say 'done'"`.
   - Confidence: high.
   - Scope: the adversary also wants a `#` inside quotes kept, and held that. The filter agent
     would leave the `#` cut alone, as about six more lines in a reader the plan says to reuse.
     The lead takes the smaller fix.

### Nit

2. **A cut line drops the next state** (C1)
   - Where: `app/Sources/SloprFlow/Renderer.swift:88-92`
   - Problem: after a partial write, the next call sends only the leftover bytes and the new
     line is lost. A write of 512 bytes or less goes in whole or not at all, so this needs a
     warning line over 512 bytes and a pipe that is nearly full.
   - Fix, if touched: cap the warning text in `HUDState.line` so every line stays under 512
     bytes, then delete `unsent` and the partial-write branch. This removes code.
   - Confidence: medium. The adversary first said fix and backed nit after the exchange.

3. **The user's command gets the app's short `PATH`** (C5)
   - Where: `README.md:133-135`
   - Problem: Homebrew and pyenv tools are not found, and `python3` is the one in `/usr/bin`.
   - Fix: one sentence in "Your own HUD": "It gets the app's short `PATH`, so give the full
     path of a tool outside `/usr/bin`."
   - Confidence: high.

### Wontfix

- C2, a missing or crashing `SloprHUD` is started again on every render: this is the plan's
  rule, and it only loops when the program we ship is broken.
- C4, a renderer that ignores the closed input outlives the app: the plan says a program ends
  when its input closes.
- C6, descriptors freed late when a launch fails: the pipe is a local, released on return.
- C7, a NaN level: `App` already turns it into 1 before `line` sees it.
- C8, the `listening` flag in `SloprHUD` repeats the phase: it does not, since the phase stays
  `.listening` after a hide.
- C9, one more read of the config at launch: the existing pattern.
- C10, `SloprHUD` registers with macOS under the app's own identity, because it sits in the
  app's bundle: the plan puts it there, the listed effects are untested, and a nested helper
  app costs more than the defect.
- C11, `renderer = " "` counts as a command: junk input, and the result is the documented one.
- C12, a line sent just after `SloprHUD` dies is lost: the plan says lines are dropped.
- C13, a fallback while thinking hides the spinner early: every warning already does this, and
  the plan keeps `App.render` as it is.
- C14, a command that puts itself in the background counts as stopped: the README already
  says what happens when the command exits.
- C15, `hud.py` blocks while speaking: that keeps the warnings in order.

### Split

None on a verdict. The only difference left is the scope of fix 1.

Candidates 15, kept 3 (1 fix, 2 nit), adversary `sol`, 2 calls: one independent read and one
exchange on C1, C11 and C14.

## Fix pass

Pass base `bec3a6d50dc7d6c0f26b8a39183d59d2eb7c4de9`. The implementer folded in all three items
and pushed back on none.

| Item | Commit | Result |
|---|---|---|
| 1. Quotes in a config value (C3) | `7f05c74` | The reader strips one matching pair of quotes. `renderer = "say 'done'"` is tested. The `#` cut is unchanged. |
| 2. A cut line drops the next state (C1) | `5cd7a4f` | A warning keeps its first 120 Unicode scalars, so a line is at most 489 bytes. `unsent` and the partial-write branch are gone, and `write` is one call. A new test covers the cap. |
| 3. The short `PATH` (C5) | `b3dd90a` | One sentence in "Your own HUD". |

## Open items

- The four app-level points of item 4 have not been run in the real app: the same pill with no
  `[hud]` section, `renderer = "cat >> states.txt"`, `renderer = "exit 1"`, and killing
  `SloprHUD` while the app runs.
- C10: `SloprHUD` registers with macOS under the app's own identity. Its effects are untested.
- A `#` inside the renderer command is still cut off as a comment.
- The cap on a warning cuts by Unicode scalar, so it can split the last character of a very
  long warning.

## Tests

At `b3dd90a`:

- `app/test.sh`: 14 tests passed
- `swift build`: both executables build
- The sidecar is unchanged.
