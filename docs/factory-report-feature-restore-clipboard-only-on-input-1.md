# Factory report: restore the clipboard only when the paste found a text input

Branch `feature/restore-clipboard-only-on-input`, base `87c73ba`.

## Work items

1. **Restore only when a text input has focus.** Landed in `d811a76`. `paste(_:)` asks
   Accessibility for the focused element and its selected-text range. With one, it behaves as
   before. Without one, ⌘V is still sent, the previous clipboard is not restored and the
   transient marker is not written.
2. **README.** Landed in `2570444`. The Permissions section says when the clipboard comes back
   and when the dictation stays on it.

## Review 1: trimmed list

Range `87c73ba..2570444`. 7 candidates, 2 kept (0 fix, 2 nit). Adversary: sol, 1 exchange.

### Fix

None.

### Nit

1. **AX queries can block the main actor.** `app/Sources/KikuFlow/Paste.swift:11`. The two
   synchronous `AXUIElementCopyAttributeValue` calls run on the main actor and wait for the
   default Accessibility timeout when the frontmost app is hung. Fix: keep the system-wide
   element in a `let` and call `AXUIElementSetMessagingTimeout(systemWide, 0.25)` before the
   first query. Cost: a slow but live app would count as "no text input". Confidence: medium.
2. **Clipboard snapshot is taken even when it is thrown away.**
   `app/Sources/KikuFlow/Paste.swift:6`. `saved` reads every pasteboard item before `restore` is
   known. Fix: compute `restore` first and build `saved` only when it is true. Confidence: high.

### Wontfix

- Read-only text counts as a text input (`Paste.swift:14`): the work file defines a text input
  by the selected-text range, and the loss in read-only views is the same as before the change.
  A possible follow-up.
- Electron apps never restore (`Paste.swift:31`): accepted by the work file and the README.
- ⌘V sent with no text input (`Paste.swift:21`): the work file asks for it.
- Force cast `focused as! AXUIElement` (`Paste.swift:14`): only reached on `.success`, where the
  value is an `AXUIElement` by contract.
- Marker left when `CGEvent` creation fails (`Paste.swift:17-25`): not a practical path, and the
  restructuring costs more than the defect.

### Split

None.
