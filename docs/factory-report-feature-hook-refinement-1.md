# Factory report: feature/hook-refinement, run 1

- Work file: `docs/plan-hook-refinement.md`
- Branch: `feature/hook-refinement`, cut from `feature/cleanup-prompts` (PR #3) at `34075b3`
- Base commit: `c1e742a41f6d727be12b8174eb2f09ceef895959`
- Reviews: 1, adversary `sol`

## Pass 0: what landed

| Item | Commit | What landed |
|---|---|---|
| 1. `on_sent` | `a5625b2` | `on_output` is renamed in `POINTS`, `after_reply`, the tests and the three READMEs. There is no alias. |
| 2. Cleanup always on, sidecar | `e56f79d` | `cleanup_enabled` is gone from the config. `Models.clean` is always a `Cleaner`. `/transcribe`, `run` and `process` take no `cleanup`. The model runs whenever there is text. |
| 3. Cleanup always on, app | `0b1299f` | The "Clean Up Text" menu item, `toggleCleanup`, the `cleanup` user default, `cleanupLoaded` and `Health.cleanupModel` are removed. `Sidecar.transcribe` sends no query. |
| 4. Return types | `4efcb60` | `fire` and `report` share `call`, which raises `TypeError("on_cleaned returned dict, not str or None")` with the hook's label. `on_done` is checked the same way. A wrong type from `on_error` is skipped and recorded. |
| 5. Docs | `c8e9197` | `examples/README.md` starts with the plan's block, followed by the nine examples. The hooks section of the top README is two sentences and the link. `sidecar/README.md` drops the query and the `enabled` key and adds the `TypeError`. |
| 6. Tests | with 1, 2 and 4 | Every case in the plan's Tests section. |

One change to the order: the rename in the READMEs went into commit 1, not commit 5, because
`test_examples.py` loads the examples as hook files and fails with the old name.

Left open by the implementer: `uv run ruff format --check` flags one test in `test_server.py`.
It did so at the base commit too, and the format check is not one of the plan's commands.

## Review 1: trimmed list

Range `c1e742a41f6d727be12b8174eb2f09ceef895959..c8e9197358d9f3f6545c91f5f966f98a7551b71e`.

The reviewer found every acceptance criterion met and no stale `on_output`, `cleanup=`,
`cleanup_enabled` or "Clean Up Text" outside `docs/`.

### Fix

None.

### Nit

1. **The `verbatim.py` introduction lost the ordering caveat** (C5)
   - Where: `examples/README.md:51-52`
   - Problem: `verbatim.py` sorts before `vocabulary.py`, so it keeps the transcript from before
     the vocabulary fixes. With both installed, a "verbatim …" dictation is pasted without them.
     The second sentence of the introduction only restates the code.
   - Fix: replace that sentence with "`vocabulary.py` sorts after it, so the transcript it
     pastes does not have the vocabulary fixes."
   - Confidence: medium. The adversary first said wontfix and backed nit after the exchange.

2. **The wrong-type test after the reply does not check that later hooks are skipped** (C15)
   - Where: `sidecar/tests/test_server.py:406-414`
   - Problem: for `on_sent` returning a dict, the test checks `errors.txt` and the missing log
     entry, but not that `on_done` was skipped. The plan's test line is met as written.
   - Fix: add `assert [c[0] for c in calls(hooks)] == ["on_transcribed", "on_cleaned", *(["on_sent"] if point == "on_done" else [])]`.
   - Confidence: high.

### Wontfix

- C1, a cleanup model that won't load blocks all dictation: the plan requires cleanup with no
  off switch, and the README gives both remedies for the gated model.
- C2, `on_done` returning a non-string is an error: the plan says it is checked the same way.
- C3, "the message goes to the HUD and `errors.txt`" is not true after the reply: the sentence
  is in the block the plan fixes word for word.
- C4, the return rule does not describe `on_error` or `on_done`: also in the fixed block, and
  the plan cuts the `on_error` paragraph.
- C6, the docs no longer say to create the hooks folder: both blocks are set by the plan.
- C7, the slow-hook and paste points are gone: the plan lists the first as deliberately not
  documented, and the signatures cover the second.
- C8, `polish.py` only catches `OSError`: untouched in this range, and the example promises
  only the case where the service doesn't answer.
- C9, the old `cleanup` user default stays on disk: harmless, and nothing needs to stay
  compatible.
- C10, `fire` special-cases `on_done`: style, and the one condition is smaller than a second
  loop.
- C11, "(below)" in the Log section: the next section still links to the file that defines
  both hooks.
- C12, the `TypeError` sentence in `sidecar/README.md` leaves out the label: the sentence
  before it explains labels.
- C13, a wrong type from `on_error` is not spelled out: the two sentences beside it cover it.
- C14, the leftover-`enabled` test does not count cleaner loads: `clean == fakes.cleaned`
  already shows the cleaner loaded and ran.

### Split

None.

### Taste

Nothing moved. There were no Fix items to weigh.

Candidates 15, kept 2 (0 fix, 2 nit), adversary `sol`, 2 calls: one independent read and one
exchange on C5 and C11.

## Fix pass

None. The Fix section was empty.

## Open items

- Nit 1: the ordering caveat for `verbatim.py`.
- Nit 2: the extra assertion in the wrong-type test.
- C3 and C4 are wontfix under the plan, but they are real: two sentences of the fixed block in
  `examples/README.md` are not true for failures after the reply and for `on_error`. Changing
  them means changing the plan's text.

## Items dropped

None.

## Tests

At `c8e9197`:

- `uv run pytest -q`: 106 passed
- `uv run ruff check .`: all checks passed
- `uv run pyright`: 0 errors
- `app/test.sh`: 7 tests passed
