# Plan: menu hotkeys and "Reload Slopr Flow"

The status menu is built in `app/Sources/SloprFlow/App.swift`, in
`applicationDidFinishLaunching`. This branch, `feature/menu-hotkeys`, starts from `main` at
`62d500d`.

## Items

1. **Give "Open Log" ⌘L.** Set its key equivalent to `"l"`.

   Accepted when: the "Open Log" item shows ⌘L and choosing it still opens `log.txt`.

2. **Give "Open Errors" ⌘E.** Set its key equivalent to `"e"`.

   Accepted when: the "Open Errors" item shows ⌘E and choosing it still opens `errors.txt`.

3. **Rename "Restart Slopr Flow" to "Reload Slopr Flow".** It keeps ⌘R and its behaviour. Rename
   the `restart()` method to `reload()` and its failure warning to "Couldn't reload: …". Update
   the user-facing docs that name the item: `README.md` and `examples/README.md`.

   Accepted when: the menu shows "Reload Slopr Flow" with ⌘R, no "Restart Slopr Flow" remains in
   the app or in `README.md` and `examples/README.md`, and the relaunch still works.

## Out of scope

- Older plans and factory reports under `docs/`. They record past work and keep the old name.
- The other menu items, their order and their key equivalents (⌘, for Config, ⌘Q for Quit).
- The global dictation hotkey (`Config.hotkey`).
