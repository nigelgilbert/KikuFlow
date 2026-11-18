# Plan: reorder the menu and drop About

The status menu is built in `app/Sources/SloprFlow/App.swift`, in
`applicationDidFinishLaunching`. This branch starts from `feature/cleanup-prompts` (PR 3) and
targets `main`.

## Items

1. **Remove "About Slopr Flow".** Delete the menu item and the `about()` method behind it, with
   the credits string it holds. Remove the README's mention of the About panel
   ("Also shown in the app's About panel."); the attribution itself stays in the README.

   Accepted when: the menu has no About item, no `about` selector or
   `orderFrontStandardAboutPanel` call remains in the app, and no doc refers to an About panel.

2. **Order the Open items as Log, Errors, Config.** The group reads "Open Log…",
   "Open Errors…", "Open Config…" from top to bottom. Titles, actions and key equivalents stay
   as they are, so "Open Config…" keeps ⌘,.

   Accepted when: the three items appear in that order in the menu, each still opens the same
   file, and any doc that states the order of the menu items matches.

## Out of scope

- The "Clean Up Text" toggle. Another branch removes it; leave it and its position alone.
- The status line, the permission items, Quit and Restart, and the separators around them. The
  separator above Quit stays, now followed by Quit and Restart only.
