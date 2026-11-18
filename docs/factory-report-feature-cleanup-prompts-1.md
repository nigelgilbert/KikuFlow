# Factory report: feature/cleanup-prompts, run 1

- Work file: `docs/plan-cleanup-prompts.md`
- Branch: `feature/cleanup-prompts`, from `hooks-followup`
- Base commit: `e7c6a5f2b823b33ed513edc1a1189528c12e7e2f`
- Reviews: 1, adversary `sol`, mode `auto`

## Pass 0: what landed

| Item | Commit | What landed |
|---|---|---|
| 1. Presets and prompt resolution | `f047566` | A `PRESETS` table and `build_messages(model, prompt_file, placement)`. `prompt_path` expands `~` and resolves relative paths against APP_DIR. A missing or empty file, a bad placement, or an unknown model without `prompt_file` is a load error. The built-in prompts keep their exact bytes. |
| 2. `safety_check` | `6b8cd4e` | `accept(raw, clean, safety_check)` sits beside the cleaner. The cap is `2n+16` with the check on and `4n+256` with it off. |
| 3. Config and server | `3768c14` | Three new `Config` fields go through the type check. `load_cleaner(config)` takes the `Config`. `/health` is unchanged. |
| 4. Config.swift | `5b12e6b` | The three keys are in the defaults, commented out, with a one-line comment each. |
| 5. Docs | `8c8f4c7` | Both READMEs list the keys; the top README has a new "Your own cleanup prompt or model" section with both caveats. |
| 6. Tests | with 1–3 | Message building, load errors, path resolution, `accept`, config keys and types, and server behaviour with the check on and off. |

Left open by the implementer: a prompt file that isn't valid UTF-8 raises a `UnicodeDecodeError` whose message doesn't name the path, and `enable_thinking=False` is still passed to every chat template.

## Review 1: trimmed list

Range `e7c6a5f2b823b33ed513edc1a1189528c12e7e2f..8c8f4c7788b6f89f5f9b73e757b2d502255b85e1`.
The reviewer found no unmet acceptance criterion.

### Fix

None.

### Nit

1. **Say what to do when a model's template has no system role** (C2)
   - Where: `sidecar/src/slopr_sidecar/cleanup.py:57`. The fix goes in `sidecar/README.md` and `README.md`.
   - Problem: an unknown model with empty `placement` gets `"system"`, as the plan says. Some chat templates reject a system turn (Gemma 2's has `raise_exception('System role not supported')`). The warm-up then fails, and `/health` shows only the template's error.
   - Fix (docs only; keep the default and don't wrap the error):
     - `sidecar/README.md`: "A model whose chat template has no system role (Gemma 2, for one) fails to load with the template's error; set `placement = "user"`."
     - `README.md`: "Use `"user"` for a model whose chat template has no system role."
   - Confidence: high.

### Wontfix

- C1 `<think>` blocks pasted with the check off: the plan says the output is used whenever it is non-empty, and the READMEs say `false` keeps whatever the model returns.
- C3 the `4n+256` cap can truncate: the cap comes from the plan and is documented. Sol backed wontfix after the exchange.
- C4 a directory is reported as "not found": the criterion holds and the error names the path. Split; see below.
- C5 "Restart" versus `/reload` in the two READMEs: both are true, and each suits its readers.
- C6 the safety-check flag is read in two places: `accept` sits beside the cleaner and `run` has a single branch, as the plan asks.
- C7 the `c = config` alias: a style preference.
- C8 `/health` doesn't show the new keys: the plan says `/health` is unchanged.
- C9 no test for the cap switch: not in the plan's test list, and testing it needs a new fake rig for a single ternary.
- C10 a ragged line in the sidecar README: there's no wrap rule, and the rendered output is the same.

### Split

- **C4** (`cleanup.py:46`). The filter agent decided it, so it sits under Wontfix.
  - Filter: wontfix. The criterion is met, a directory there is rare, and the path in the message makes the cause obvious.
  - Sol: nit, and it held after the exchange. A directory that exists is reported as "not found", and a small wording change would fix it.

### Counts

10 candidates, 1 kept (0 fix, 1 nit), 9 wontfix (1 of them split). Adversary `sol`, 1 exchange.

## Fix pass 1

| Item | Result |
|---|---|
| Nit 1 (no system role) | Taken as proposed, no pushback: `520e7e3`. Both READMEs now say to set `placement = "user"` for templates without a system role, and the touched paragraphs are rewrapped. |

## Open items

- C4 (split): a directory set as `prompt_file` is reported as "not found". Left as wontfix by the filter agent; Sol would make it a nit.
- From the implementer: a prompt file that isn't valid UTF-8 raises a `UnicodeDecodeError` that doesn't name the path, and `enable_thinking=False` is passed to every chat template without being checked against other models.
- Out of scope by decision: any `[stt]` prompt, vocabulary or Parakeet booster.

## Tests

`cd sidecar && uv run pytest -q && uv run ruff check . && uv run pyright`: 80 passed, ruff clean, pyright 0 errors. `app/test.sh`: 7 tests passed.
