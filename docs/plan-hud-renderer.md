# Plan: a one-call renderer interface for the HUD

The HUD is driven today by five calls on `HUD` (`listen`, `level`, `think`, `warn`, `dismiss`),
and `HUD` also owns the warning's auto-hide timer and the level scaling. The goal is the
smallest interface that supports what the app does now, so that a different renderer can be
swapped in later. This change keeps the builtin look and behaviour exactly as it is; it adds no
config key and no new renderer.

The interface:

```swift
enum HUDState: Equatable {
    case hidden
    case listening(level: Float)   // 0...1, the newest mic level
    case thinking
    case warning(String)
}

@MainActor protocol Renderer { func render(_ state: HUDState) }
```

## Items

1. **Add `HUDState` and `Renderer`, and make the builtin conform.** Rename `HUD` to
   `BuiltinRenderer` (file `HUD.swift` may become `Renderer.swift` / `BuiltinRenderer.swift`)
   with `render(_:)` as its only non-private member. It keeps its own 32-sample level history:
   a transition into `.listening` from any other state clears the history, then each
   `.listening(level:)` appends its level. `.hidden` orders the panel out. The panel setup, the
   placement and the SwiftUI view stay as they are, and it holds no timers.
   *Acceptance*: `BuiltinRenderer` exposes only `init()` and `render(_:)`; the bars, spinner,
   warning text and placement look and behave as before.

2. **Move the behaviour rules into `App`.** `App` holds `any Renderer` (the builtin), and all
   HUD updates go through `render`. The 1.5 s warning auto-hide moves into `App`: a warning
   schedules `render(.hidden)` after 1.5 s, and any later `render` call before then cancels it,
   exactly as `show` cancelled `hide` before. The scaling `min(1, rms * 12)` moves into `App`, so
   renderers always receive a level in 0...1.
   *Acceptance*: `listen`, `level`, `think`, `warn` and `dismiss` no longer exist; every warning
   still hides after 1.5 s unless something else is shown first.

3. **Drop levels that arrive after listening ends.** `Recorder` sends each level through its own
   `Task { @MainActor … }`, so one can land after `stop()` and the switch to thinking. `App`
   forwards a level only while `activity == .listening`, so a late level can never switch the HUD
   back to listening.
   *Acceptance*: the level callback checks `activity == .listening` before rendering.

## Constraints

- Keep the diff small and match the existing style: short doc comments only where they explain a
  why, no new dependencies.
- `app/test.sh` must pass (it builds the app target too). The interface adds no AppKit-free logic
  that needs new tests; add one only if a piece lands somewhere testable without AppKit.
