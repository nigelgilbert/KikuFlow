# Hotkey combos

The hold-to-talk hotkey is one modifier key today. This work lets it be a combo: several
modifiers, or modifiers plus one normal key, written as one string in `config.toml`.

```toml
[hotkey]
key = "right_option"                 # still valid
key = "right_option+right_command"   # hold both
key = "right_option+space"           # hold Option, then Space
```

The aim is the smallest change that does this well. Keep the hand-written config reader; add no
package dependency. Prefer changing the existing types over adding new ones, and add no
abstraction that only one caller uses.

## Background

- `app/Sources/KikuFlow/Hotkey.swift`: `Hotkey.Key` (title, key code, device modifier mask), the
  `named` table of seven modifiers, the event tap, and `update(keyCode:flags:)`, which the tests
  drive directly.
- `app/Sources/KikuFlow/Config.swift`: `hotkey(in:)` looks one name up in `Hotkey.Key.named` and
  falls back to Right Option without a word. `defaults` is the text of a new `config.toml`.
- `app/Sources/KikuFlow/App.swift`: uses `key.title` in the menu's ready line and in two HUD
  warnings, and `render(.warning(...))` to show a warning.
- Tests are in `app/Tests/KikuFlowTests/`; run them with `app/test.sh`.

## Items

### 1. Read a combo from the config

`[hotkey] key` is a list of names joined by `+`. Spaces around a name are ignored. The names are
the seven modifiers there are today, and `space`, the first normal key.

A value is valid when every name is known, it has at least one modifier, and it has at most one
normal key. A normal key by itself is not valid: it would take that key away from every app.

Acceptance:

- `"right_option"`, `"right_option+right_command"`, `"right_option+space"` and
  `"right_option + space"` each give that combo.
- A missing `key` gives Right Option and no warning.
- `"caps_lock"`, `"right_option+caps_lock"`, `"space"`, `"right_option+space+space"`, `""` and
  `"right_option+"` are not valid. The app then uses Right Option and shows one HUD warning at
  launch that names the value as written, for example
  `Unknown hotkey "caps_lock". Using Right Option.`
- The combo's title joins its keys' titles with ` + `, in the order written: `Right Option + Space`.
  The menu's ready line and the HUD warnings that name the key use it.
- The menu's ready line shows the whole title of a combo; the 30-character cut still applies to
  the other status lines.
- `ConfigTests` covers each bullet above that the config reader decides.

### 2. Fire on a combo, and swallow its normal key

The combo is down when all its modifiers are held and, if it has a normal key, that key is
captured. `onChange` fires once when the combo goes down and once when it goes up, as today.

Rules:

- Which modifiers are held comes from `flagsChanged` events only. Key-down and key-up events
  also carry flags, but an arrow or function key sets the Fn flag on its own events, so reading
  them would fire an `fn` hotkey by mistake.
- A key-down of the combo's normal key while all its modifiers are held captures the key. While
  it is captured, its key-downs (the first and every repeat) and its key-up are swallowed: the tap
  callback returns nil for them, so the focused app never gets them. Its key-up ends the capture.
- A key-down of the normal key while a modifier is missing passes through and captures nothing.
  Pressing the modifiers afterwards, with the key still held, does not fire.
- Letting go of a modifier first ends the combo, and the normal key stays captured, and
  swallowed, until it comes up.
- Any other key is passed through untouched. A combo of modifiers only swallows nothing.
- The tap asks for key-down and key-up events only when the combo has a normal key, so a
  modifier-only hotkey leaves ordinary typing out of the app's event tap, as today.
- When the tap is re-enabled after a timeout, the held state is read again for every key of the
  combo, as it is for the one key today.

Keep a seam the tests can drive without an event tap, as `update(keyCode:flags:)` is today; its
shape may change. It reports whether the event is to be swallowed.

Acceptance:

- The two tests in `HotkeyTests` still pass, changed only as far as the seam's shape needs.
- New tests, one each:
  - two modifiers fire only while both are held, in either press order;
  - modifier then Space fires once, repeats of Space fire nothing, and every Space event is
    swallowed;
  - Space without the modifier is not swallowed and fires nothing, also when the modifier is
    pressed afterwards;
  - letting go of the modifier before Space fires the release once, and Space's later repeats and
    key-up are still swallowed;
  - with `fn+space`, a key-down of another key that carries the Fn flag fires nothing;
  - a modifier-only combo swallows nothing.
- `swift build` in `app/` has no new warnings.

### 3. Describe it where the config is described

Acceptance:

- The `[hotkey]` comment in `Config.defaults` says a combo is names joined by `+`, lists the
  modifier names and `space`, and gives one example.
- The `[hotkey]` block of the config example in `README.md` matches `Config.defaults`. Change
  nothing else in the README.
- `ConfigTests` still reads `Config.defaults` as Right Option.

## Out of scope

- Exact matching: `right_option+space` also fires while another modifier is held.
- Normal keys other than `space`.
- A TOML package, or an array form of `key`.
- A warning for a bad `[server] port`.
- The sidecar, and `Sidecar.swift`, which another branch is changing.
