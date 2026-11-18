# Factory report: feature/menu-order, run 1

Work file: `docs/plan-menu-order.md`. Branch `feature/menu-order`, cut from
`feature/cleanup-prompts` (PR 3) at `34075b3`. Base commit for the run: `b0de0b6`. One review,
adversary Sol.

## Work items

1. **Remove "About Slopr Flow".** Landed in `2980fef`. The menu item and the `about()` method
   with its credits string are gone from `app/Sources/SloprFlow/App.swift`. The README no longer
   says the attribution is shown in the About panel; the attribution itself stays.
2. **Order the Open items as Log, Errors, Config.** Landed in `71e3aa4`. Titles, actions and
   key equivalents are unchanged, and "Open Config…" keeps ⌘,. No doc states the menu order, so
   no doc changed.

## Review 1: `b0de0b6..71e3aa4`

The reviewer found both acceptance criteria met and raised two candidates.

**Fix**: none.

**Nit**: none.

**Wontfix**

- `app/Sources/SloprFlow/App.swift:73`, the in-app Parakeet attribution is gone. The plan asks
  for this removal and requires the attribution only in the README, where it stays at
  `README.md:127-130`. Adding a `Credits.rtf` or an `NSHumanReadableCopyright` entry is outside
  the plan. See the open items.
- `README.md:44`, `:104`, `:108`, the README covers Config before Log and Errors. These are
  topic sections and do not state a menu order, so the criterion does not apply.

**Split**: none.

Candidates 2, kept 0, adversary Sol, 1 exchange. The filter agent and Sol agreed on the first
call.

## Fix pass

None. The trimmed list had no Fix or Nit items.

## Open items

- The built app now carries no CC-BY-4.0 credit for NVIDIA Parakeet TDT 0.6B v3. `app/bundle.sh`
  copies only `scripts/` and `sidecar/`, so the README is not in the bundle, and the Info.plist
  has no copyright key. The bundle holds no model weights; the sidecar downloads them by model
  id. Whether the app should carry the credit inside the bundle is a decision for the owner and
  would be a separate work item.

## Tests

`app/test.sh`: 7 tests passed, 0 failed. The sidecar checks were not run because nothing under
`sidecar/` changed.
