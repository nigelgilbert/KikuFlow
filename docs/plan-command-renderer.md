# Plan: the HUD as a program the user can replace

The HUD goes through one call, `render(_ state: HUDState)`, and `App` always draws it with
`BuiltinRenderer`, inside the app. This plan turns the renderer into a separate program that
receives the HUD states as plain lines. The pill we ship becomes one such program, `SloprHUD`,
and the config can name another, in any language.

```toml
[hud]
renderer = "python3 hud.py"   # a command of yours; empty means the pill that comes with the app
```

```
app → render(state) → one line on the program's standard input
```

## Rules

- **The app always talks to a program.** There is no in-app renderer any more. With `renderer`
  empty or missing, the program is `SloprHUD`, the executable beside the app's own.
- **The config holds a command, not a file.** It runs through `/bin/sh -c`, with
  `~/Library/Application Support/SloprFlow/` as the working directory, so `python3 hud.py` finds
  a file beside the config and needs no executable bit. `SloprHUD` is started directly.
- **One program, started once.** The app starts it at launch and keeps it running. Its standard
  input is a pipe from the app; its output and errors go where the app's go.
- **One plain line per state.**

  | State | Line |
  |---|---|
  | `.hidden` | `hidden` |
  | `.listening(level:)` | `listening 0.42`, the level in 0...1 with two decimals |
  | `.thinking` | `thinking` |
  | `.warning(text)` | `warning ` and the text, with line breaks turned into spaces |

- **The app keeps the behaviour rules.** The 1.5 s hide after a warning and the level scaling
  stay in `App`, so a program only shows what it is told and gets `hidden` when it is time.
- **A program ends when its input closes.** That is how it stops when the app quits or dies.
- **A broken renderer never takes the app down.**
  - If the user's command can't start, or exits, the app starts `SloprHUD` in its place and
    renders `.warning("The HUD renderer stopped")`. The command is not tried again until the
    app restarts.
  - If `SloprHUD` itself is not running when a state is rendered, the app starts it again
    first.
  - If a program stops reading, lines are dropped.

## Items

1. **Read `[hud] renderer` from the config.** Add `Config.renderer`, read with the same reader
   as `port` and `hotkey`; missing or empty means `SloprHUD`. Add a `[hud]` section with a
   commented `# renderer = ""` line to `Config.defaults`.
   *Acceptance*: tests for the key present, missing and empty, beside the existing config
   tests.

2. **Give `HUDState` its line.** A `line` property on `HUDState` returns the text in the table
   above, without the newline.
   *Acceptance*: one test per state, including a level rounded to two decimals and a warning
   whose text has a line break.

3. **Add the `SloprHUD` program.** A second executable target in `app/Package.swift`, with its
   source in `app/Sources/SloprHUD/`.
   - It holds what `BuiltinRenderer` and `HUDView` hold today: the panel, the notch placement,
     the 32-sample level history and the SwiftUI view. The pill looks and behaves as before.
   - It reads lines from standard input, shows each state, ignores a line it doesn't know, and
     exits when the input closes.
   - It runs as an accessory app: no Dock icon and no menu bar, and it never takes focus.
   - It shares no code with the app target, so its source reads as a complete example of a
     drawn renderer.
   *Acceptance*: `swift build` builds both executables. Piping `thinking`, a few `listening`
   lines, `warning Hello` and `hidden` into `SloprHUD` shows each in turn, and it exits when the
   pipe closes.

4. **Make `Renderer` the pipe to a program.** `Renderer` becomes a final class in the app
   target, in place of the protocol and `BuiltinRenderer`, which leave the app.
   - It starts the program as described under Rules, and `render` writes the state's line and
     a newline to the pipe.
   - The app ignores `SIGPIPE`, so writing to a program that has gone does not kill it.
   - The pipe's write end is non-blocking, and a line that can't be written is dropped.
   - The fallbacks are the ones under Rules.
   - On quit the app closes the pipe.
   *Acceptance*:
   - With no `[hud]` section, dictation shows the same pill as today.
   - With `renderer = "cat >> states.txt"`, a dictation leaves `listening …` lines, `thinking`
     and `hidden` in `states.txt` beside the config, and no pill appears.
   - With `renderer = "exit 1"`, the warning shows in the pill and later dictations use it.
   - Killing `SloprHUD` while the app runs brings it back on the next dictation.

5. **Bundle the program.** `app/bundle.sh` copies `SloprHUD` into `Contents/MacOS/` beside
   `SloprFlow` and signs it with the same identity before the bundle is signed.
   *Acceptance*: the built bundle holds both executables and `codesign --verify --deep` passes
   on it.

6. **Example and docs.**
   - `examples/hud.py`: the smallest useful renderer, which speaks each warning with `say` and
     ignores the other states.
   - Top `README.md`: a short "Your own HUD" section after "Lifecycle hooks" with the config
     key, the four lines, `examples/hud.py`, and `app/Sources/SloprHUD/` as the example of a
     drawn one. Add `[hud]` to the config block.
   *Acceptance*: `examples/hud.py` works when copied beside the config and named in it.

## Constraints

- Keep the diff small and match the existing style: short doc comments only where they explain
  a why, no new dependencies.
- `HUDState` keeps its four cases. `App.render` keeps the warning hide as it is.
- `app/test.sh` must pass. The sidecar does not change.

## Out of scope

- Trying the user's command again after it exits.
- Sending a program anything besides the four states, such as the dictated text.
- Reading anything back from a program.
- Choosing the pill's look from the config.
