# Factory report: lifecycle hooks follow-up

- Work file: `docs/plan-hooks-followup.md`
- Branch: `hooks-followup`, base commit `8a0868d4136679a319d54e43d9e3945a770553fb`
- Reviews: 1, with `astra` as the adversary

## Work items

All six items landed, one commit each.

| Item | What landed | Commit |
|---|---|---|
| 1. Hooks take and return plain text | `Utterance` and the `at` timestamp are gone. `fire(hooks, point, text)` hands each hook a `str` and returns the text for the next phase. | `912e38c` |
| 2. Move the log into core | `slopr_sidecar/hooks/` is deleted. `lifecycle.write_log` writes `log.txt`, and `load_hooks` reads the one user directory. `server.after_reply` writes the log after the reply and logs a failed write. | `e43c2fc` |
| 3. Rename `on_logged` to `on_done` | Renamed everywhere outside `docs/`, with no alias. | `42abac4` |
| 4. Add `on_output` | `after_reply` fires `on_output`, stops if the text is empty, writes the log, then fires `on_done`, all on the executor after the response. | `066166b` |
| 5. Rework `examples/README.md` | Diagram, table and four signatures up front; seven example hook files, all using `t`; `on_output` and `on_done` examples replace the log override. | `a4c221e` |
| 6. Update the READMEs | Both name the four hooks and describe the log as something the app always keeps. | `45ba5fd` |

One criterion was met differently from the plan: item 3 has no test that a function named
`on_logged` is ignored, because the test would have to contain that name and the same item
says it appears nowhere in the tests. A name outside the four hook names is never loaded.

No Swift changed. "Open Log…" already opens `log.txt`.

## Review 1: trimmed list

Range `8a0868d4136679a319d54e43d9e3945a770553fb..45ba5fd0993a0a49114363066c3d9c735c766866`.
"C3" means candidate 3 in the reviewer's list.

### Fix

1. **`private.py` matches any word that starts with "private"** (C3),
   `examples/README.md:136-140`. `t.lower().startswith("private")` has no word boundary, so
   "Privately held firms." is pasted but silently left out of the log, and `on_done` never
   fires for it. Fix: `if re.match(r"private\b", t, re.IGNORECASE): return ""`, with
   `import re`. Confidence: high.

### Nit

2. **"Hooks run one dictation at a time" is not strictly true** (C1),
   `examples/README.md:46-48`. A dictation's `on_output` and `on_done` are queued after its
   reply is sent, so a second request already waiting runs its `on_transcribed` first. The
   filter agent reproduced it: with `raw_log.py` installed, overlapping requests logged the
   second transcript twice. The app sends one dictation at a time, and reaches this only when
   a request outlives its 120 s timeout. Fix: change the sentence to "The app sends one
   dictation at a time, so a hook file can keep state between its own hooks in module
   variables." No code change. Confidence: medium.
3. **`timed_log.py` writes two spaces that the log flattens to one** (C8),
   `examples/README.md:131`. Fix: one space. Confidence: high.
4. **`verbatim.py` pastes text without the vocabulary fixes** (C4),
   `examples/README.md:83-85`. `verbatim.py` sorts before `vocabulary.py`. Fix: add
   "`vocabulary.py` also sorts after it, so the transcript it keeps, and pastes, does not have
   the vocabulary fixes." Confidence: high.
5. **The examples omit that slow after-reply hooks hold up the next dictation** (C13),
   `examples/README.md:35-37`. Fix: "…so they don't delay the paste, but a slow one holds up
   the next dictation." Confidence: high.
6. **`archive.py` "keeps every dictation" overstates** (C7), `examples/README.md:145`.
   `on_done` does not fire when an `on_output` returns `""`. Fix: "keeps every logged
   dictation". Confidence: high.
7. **"one paragraph each" contradicts the other two docs** (C10), `README.md:89`. Fix: "one
   line each". Confidence: high.
8. **Unused `import asyncio` in the RECORDER source** (C22),
   `sidecar/tests/test_server.py:19`. Fix: delete the line inside the string. Confidence:
   high.
9. **Test name is narrower than what it asserts** (C23), `sidecar/tests/test_server.py:208`.
   Fix: rename to `test_run_leaves_on_output_and_on_done_for_after_the_reply`. Confidence:
   high.
10. **`verbatim.py` strips only `,` and `.` after the keyword** (C6),
    `examples/README.md:98`. Fix: `first.strip(",.:;!?")`. Confidence: low; nobody has shown
    either speech engine producing that punctuation after a spoken first word.

### Wontfix

- **C2**, ordering after-reply work before the next request in `server.py`: costs module-level
  state and can run after-reply hooks before the reply, for a path the app reaches only after
  a 120 s hang.
- **C5**, bare "verbatim" pastes nothing: follows the empty-text rule.
- **C9**, `datetime.now()` drift: the work file settles that a hook calls `datetime.now()`.
- **C11**, "return the text for the next phase" said of all four hooks: restates the work
  file's one rule.
- **C12**, "once the log entry has been written" when the write failed: the work file's words,
  and the failure is already logged.
- **C14**, "The log is always written": the work file asks for the log to be described as
  always kept, and the sentence before gives the exception.
- **C15**, "one utterance" in `sidecar/README.md:47`: plain English on an untouched line.
- **C16**, whitespace-only text writes a blank entry: only a hook returning `" "` reaches it,
  and the next write removes the blank.
- **C17**, non-atomic `write_text`: inherited, and hardening beyond the minimal bar.
- **C18**, `point != "on_done"` inside `fire`: one condition implements the rule; moving it
  costs lines.
- **C19**, warn on unknown `on_*` names: a new feature the work file does not ask for.
- **C20**, test that `on_logged` is not called: contradicts the criterion that the name
  appears nowhere in the tests.
- **C21**, test checks the log exists, not its content: with one dictation in a fresh
  directory, absent at `on_output` and present at `on_done` proves the order.
- **C24**, `log` / `LOG` naming: style preference with no rule behind it.
- **C25**, "private" stays in the pasted text: the prose says so, and stripping it makes the
  example longer than its idea.
- **C26**, behaviour tests for the examples: the work file only requires that every block
  loads.

### Split

None.

### Counts

26 candidates, 10 kept (1 Fix, 9 Nit), 16 Wontfix, 0 Split. Adversary `astra`; 18 of 26
verdicts agreed on the first call, and one exchange settled the other 8.

No Fix item was split, low confidence or a taste call, so the list went to the fix pass
without a human check.

## Fix pass

Pass base `6efb2520441ee53a790fe9907c10f614d355ae73`. The implementer folded in 9 of the 10
items.

| Item | Result | Commit |
|---|---|---|
| 1. `private.py` word boundary | Folded in | `97491f9` |
| 2. "one dictation at a time" wording | Folded in | `97491f9` |
| 3. `timed_log.py` single space | Folded in | `97491f9` |
| 4. `verbatim.py` and the vocabulary fixes | Folded in | `97491f9` |
| 5. Slow after-reply hooks hold up the next dictation | Folded in | `97491f9` |
| 6. "keeps every logged dictation" | Folded in | `97491f9` |
| 7. "one line each" in `README.md` | Folded in | `97491f9` |
| 8. Unused import in the RECORDER source | Folded in | `af07d67` |
| 9. Test rename | Folded in | `af07d67` |
| 10. Wider punctuation strip in `verbatim.py` | Not folded in | |

Pushback on item 10: the implementer declined it because nobody has shown either speech
engine putting `:`, `;`, `!` or `?` after a spoken first word, so the change would guard
against a case nobody has seen. It was the only low-confidence item. The lead agreed and it
stays open.

## End-to-end check

Run after the fix pass, at `af07d67`, because the unit tests use fake models. The branch's
sidecar was started on a spare port with the real Parakeet and cleanup models, in a temporary
home directory so the user's own `log.txt` was not written (its size and modification time
were the same before and after).

- **No hook files.** Three spoken recordings made with `say` were posted to `/transcribe`.
  Each reply came back with text, and `log.txt` then held exactly the three replies, in
  order, one line each with one blank line between.
- **A hook file with `on_output` and `on_done`.** After `/reload`, a fourth request's reply
  was unchanged, the new log entry was the text `on_output` returned, and `on_done` received
  that text with the entry already in the file.

Not covered: the hotkey, the microphone and the paste, which need a person at the app.

## Open items

- **Overlapping requests and module variables.** A hook file that stores the transcript in
  `on_transcribed` and reads it in `on_output` or `on_done` gets the later transcript if a
  second request reaches the sidecar before the first one's after-reply work has run. The app
  sends one dictation at a time and reaches this only when a request outlives its 120 s
  timeout; any other client that overlaps requests reaches it every time. The examples now
  state the app's behaviour instead of promising the order. Ordering it in `server.py` was
  judged out of proportion (C2).
- **`verbatim.py` punctuation** (item 10 above): left as `strip(",.")`.
- **No test that a function named `on_logged` is ignored**, for the reason given under Work
  items.
- **Not checked by hand:** a dictation through the running app, and "Open Log…" showing it.

No items were struck by the user.

## Tests

- Sidecar, from `sidecar/`: `uv run pytest -q && uv run ruff check . && uv run pyright` gives
  58 passed, ruff clean, pyright 0 errors (48 tests at the base commit).
- App: `app/test.sh` gives 7 tests passed. No Swift changed.
- End-to-end with the real models: passed, as described above.
