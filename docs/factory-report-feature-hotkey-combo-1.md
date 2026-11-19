# Factory report: feature/hotkey-combo, run 1

Work file: `docs/hotkey-combo.md`. Base commit: `5a3634b`. One filtered review, adversary Sol.

## Review 1: trimmed list

Range `5a3634b..d52ffed`. 12 candidates, 3 kept (1 fix, 2 nit). One exchange with Sol; no splits.

### Fix

1. **Re-enable path reads the normal key one way only.** `app/Sources/KikuFlow/Hotkey.swift:74`
   (with `:87`).
   - Problem: after the tap is disabled and re-enabled, the reconcile only repairs held → up. A
     Space key-down the tap never saw leaves `normalHeld == false`, so the next autorepeat with
     the modifiers held counts as a first press: it captures, `onChange(true)` fires mid-hold, and
     later repeats are swallowed. That breaks "Pressing the modifiers afterwards, with the key
     still held, does not fire" on this path, and only half meets "the held state is read again
     for every key of the combo".
   - Fix: reconcile both ways at line 74:
     `if let normal { if held(normal) { normalHeld = true } else if normalHeld { update(.keyUp, keyCode: Int64(normal.code), flags: 0) } }`
     and reword the comment above it to cover both directions.
   - Confidence: high.

### Nit

2. **Typing can stall briefly at Quit or Reload with a normal-key combo.**
   `app/Sources/KikuFlow/Hotkey.swift:49-50`, `app/Sources/KikuFlow/App.swift:84-87`.
   - Problem: with `right_option+space`, every key-down and key-up goes through the tap on the
     main run loop. `applicationWillTerminate` runs `sidecar.stop()`, which busy-waits up to 2 s,
     so keystrokes are held meanwhile. Once, at exit; no acceptance bullet is unmet.
   - Fix, if wanted: add `func stop() { if let tap { CGEvent.tapEnable(tap: tap, enable: false) } }`
     to `Hotkey` and call it first in `applicationWillTerminate`. Leaves `Sidecar.swift` untouched.
   - Confidence: medium (Sol first said fix, then backed nit).

3. **"Names the value as written" is untested for a value with inner spaces.**
   `app/Tests/KikuFlowTests/ConfigTests.swift:37`.
   - Problem: the code is right, but no invalid test value has spaces around a name.
   - Fix: add `"right_option + caps_lock"` to the invalid list in
     `hotkeyDefaultsWhenMissingOrInvalid`.
   - Confidence: high.

### Wontfix

- Warning easy to miss (`App.swift:74`): the work file asks for one HUD warning at launch.
- `normalHeld`/`captured` stuck after a lost key-up (`Hotkey.swift:87-91`): speculative, heals
  after one Space press; polling `keyState` on every event costs more than the defect.
- Duplicate modifiers accepted (`Config.swift:50`): not forbidden by the work file; the only
  effect is an odd menu title.
- "Unknown hotkey" for known-but-invalid values (`Config.swift:51`): the wording is the work
  file's own example and a test asserts it.
- Stale paragraph under the config block (`README.md:74-76`): real, but item 3 says to change
  nothing else in the README. Listed under Open items.
- `flags` not seeded at `start()` (`Hotkey.swift:31,42`): same behaviour as before the change.
- Synthetic keyCode 0 on re-enable (`Hotkey.swift:72`): cannot match `space`; other normal keys
  are out of scope.
- Press order only partly covered (`HotkeyTests.swift:33-43`): the second cycle already presses
  Option with Command held.
- No test for the re-enable reconcile (`Hotkey.swift:69-75`): not listed in the work file, and it
  would need a single-caller function extracted.

### Split

None.

## Work items

1. **Read a combo from the config.** `f97a7fd`. `Config.hotkey(in:)` splits `key` on `+`, checks
   the combo and returns the keys with a warning for a value that isn't valid; the app shows the
   warning once at launch. `space` joins the key table. The menu's ready line shows the whole
   combo title.
2. **Fire on a combo, and swallow its normal key.** `9c95a64`. `Hotkey` holds the modifiers and
   an optional normal key. Modifier state comes from `flagsChanged` only; the normal key is
   captured on a first press with the modifiers held and swallowed until it comes up. The tap asks
   for key events only when the combo has a normal key. Six new tests.
3. **Describe it where the config is described.** `d52ffed`. The `[hotkey]` comment in
   `Config.defaults` and the same block in `README.md`.

Decided by the implementer where the work file was silent:

- Every value that isn't valid gets the "Unknown hotkey" wording, also `"space"` on its own.
- A repeated modifier (`right_option+right_option`) is accepted.
- After a modifier is let go while Space is still held, pressing the modifier again does not
  start a new recording; Space has to come up first.

## Fix pass 1

Pass base `670782f`. All three items taken, no pushback.

1. Re-enable reads the normal key both ways: `b2159c1`.
2. Disable the tap first when quitting: `c4028c0`. `Hotkey.stop()`, called first in
   `applicationWillTerminate`.
3. Test a warning value with inner spaces: `4333a3b`.

## Open items

- The paragraph under the config example in `README.md` (lines 74-76) still says a name that
  isn't in the list falls back to Right Option, and names only `key = "fn"` in the Fn advice.
  Left alone because the work file limits README changes to the `[hotkey]` block.
- Not checked on a live keyboard: that a swallowed Space and its repeats never reach the focused
  app; that arrow and function keys don't fire an `fn` combo; the tap's re-enable path; that the
  launch warning shows in the HUD; that a modifier-only hotkey gets no key events. The tests drive
  the state logic only.

## Tests

`app/test.sh`: 21 tests passed (14 before this work). `swift build` in `app/`: no warnings.
