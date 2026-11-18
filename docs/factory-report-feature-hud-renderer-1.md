# Factory report: feature/hud-renderer, run 1

- Work file: [plan-hud-renderer.md](plan-hud-renderer.md)
- Branch: `feature/hud-renderer`, from `origin/main` (cfac45a). Base commit 16afd23 (the plan).
- Mode: factory-v2, 1 review, adversary `sol`, `auto`.
- Test command: `app/test.sh` (builds the app target and runs the Swift tests).

## Work items

1. **HUDState and the Renderer protocol; HUD becomes BuiltinRenderer.** 11a4ab7. `HUD.swift`
   was renamed to `Renderer.swift` and now holds `HUDState`, `@MainActor protocol Renderer` and
   `BuiltinRenderer`. `BuiltinRenderer` exposes only `init()` and `render(_:)`, owns its 32-sample
   history (cleared on entering `.listening`) and holds no timers.
2. **The behaviour rules move into App.** d481c01. `App` holds `any Renderer`. One private
   `render(_:)` cancels any pending hide, renders, and for a `.warning` schedules `.hidden` after
   1.5 s. The `min(1, rms * 12)` scaling is in the level callback. The five old methods are gone.
3. **Levels that arrive after listening ends are dropped.** f8bec4a. The level callback renders
   only while `activity == .listening`.

## Review 1 (16afd23..f8bec4a): trimmed list

### Fix

None.

### Nit

1. **A warning during a hold is replaced by the next mic level.** `App.swift:122`, with `:149`
   and `Renderer.swift:44-47`. A warning rendered while `activity == .listening` lasts about one
   audio buffer: the next level cancels the hide and `BuiltinRenderer` brings the bars back. The
   old `HUD.level()` only changed the history, so the warning stayed for 1.5 s and the panel then
   stayed hidden until `think()`. The only path that reaches this is a failed `relaunch.run()` in
   `restart()` with the hotkey held. Fix: an `App` flag `showLevels`, set true just before
   `render(.listening(level: 0))` in `startListening`, set false in `render` on `.warning`, and
   checked in the level callback with `activity == .listening`. Confidence: medium (Sol first said
   fix, then backed nit).

### Wontfix

- Auto-hide during `.thinking` leaves the spinner hidden: not a regression; the old `warn()`
  did the same, and the plan keeps the behaviour.
- Move the late-level filter into `Recorder`: plan item 3 names the App-side check.
- `if case .listening = previous {} else {…}`: style preference with no repo rule; a Bool flag
  is the same state.
- Per-level `hide?.cancel()` and two array mutations: negligible cost; the mutations are
  unchanged from the old code, and the proposed `hide == nil` check never fires.

### Split

None.

Candidates 6, kept 1 (candidates 1 and 6 merged into one Nit), adversary `sol`, exchanges 2.

## Fix pass 1

- Nit 1: not folded in; no commit. The implementer agreed the behaviour change is real but
  pushed back: the only path is a failed `/bin/sh` launch from Restart with the hotkey held; the
  `showLevels` flag would spread HUD state across `App` for a path that in practice never runs;
  and bringing the bars back while the mic is still recording is arguably better than the old
  silent hide. The lead accepted the pushback in one exchange.

## Open items

- Nit 1 (warning during a hold is replaced by the next level) is left as is. If exact parity is
  wanted, the `showLevels` flag above is the fix.
- The look was not checked by hand; the tests cover the build and the existing logic only.
- Not in scope: a `[hud] renderer = …` config key and any non-builtin renderer.

## Tests

`app/test.sh`: build succeeds, 7 tests pass (unchanged count; nothing new is testable without
AppKit).
