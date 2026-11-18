# Plan: user-supplied cleanup prompts

Starts from `hooks-followup` (PR #2). It makes the cleanup step configurable: the user can
replace the prompt, choose where it goes in the chat, use any mlx-lm chat model, and turn off
the safety check that would otherwise throw away output from prompts that are not a cleanup.
Speech recognition is out of scope: no prompt or vocabulary options for `[stt]`.

## Today

`cleanup._prompt` hard-codes, for each of two supported models, the prompt text and its
placement:

- `ReFyneLabs/simplewords-dictation-cleanup-v3`: `system_v2.txt` downloaded from the model repo,
  stripped, put in the single user turn as `f"{system}\n\n{raw}"`. No system role.
- `devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit`: `utter_system.txt` from the
  package, byte for byte with its final newline, as the system turn; `raw` is the user turn.

Any other model raises `unsupported cleanup.model`. `server.run` keeps the model output only
when `is_plausible(raw, clean)`, and `clean` caps `max_tokens` at `2 * input tokens + 16`.

## Config

```toml
[cleanup]
enabled = true
model = "ReFyneLabs/simplewords-dictation-cleanup-v3"
prompt_file = ""       # a text file whose contents replace the model's built-in prompt
placement = ""         # "system" or "user"; empty means the model's built-in placement
safety_check = true    # false keeps whatever the model returns
```

- `prompt_file`: `~` is expanded; a relative path is resolved against
  `~/Library/Application Support/SloprFlow/`. Empty means the built-in prompt. The file is read
  when the models load, so `/reload` (and "Restart Slopr Flow") picks up edits. A missing or
  empty (whitespace-only) file is a load error shown through `/health`'s `error`, naming the
  path.
- `placement`:
  - `"system"`: the prompt is the system turn, verbatim, and the transcript is the user turn.
  - `"user"`: one user turn, `f"{prompt.strip()}\n\n{raw}"`, no system turn.
  - Empty: the built-in model's placement, or `"system"` for any other model.
  - Any other value is a load error.

  The built-in prompts keep their current exact bytes under this rule (ReFyne is `user`, so
  stripped; Utter is `system`, so verbatim).
- `model`: any mlx-lm chat model is allowed when `prompt_file` is set. An unknown model without
  `prompt_file` is a load error that says to set `cleanup.prompt_file`. A built-in model with
  `prompt_file` set uses the file and does not download or read its built-in prompt.
- `safety_check`: `true` keeps today's behaviour exactly, including the `max_tokens` cap. With
  `false`, the model output is used whenever it is non-empty after `strip()` (empty output still
  falls back to the transcript), and the cap becomes `4 * input tokens + 256` so a prompt that
  expands text (an email, a translation) is not cut off while a runaway generation still stops.
- New keys go through the existing type check in `load_config` (all strings except
  `safety_check`, a bool).

## Code

- `cleanup.py`: replace the `match` with data: a table of built-in presets (model name →
  how to get the prompt text, placement) and one function that, from model, `prompt_file`,
  `placement`, returns the `raw -> messages` function. Keep it callable in tests without
  downloading anything when `prompt_file` is set. `load_cleaner` takes the cleanup settings
  (pass the `Config` or the three values; implementer's choice, keep it small). The safety
  check decision moves next to the cleaner so `server.run` stays a single "use the candidate or
  not" branch.
- `config.py`: the three new fields with defaults above.
- `server.py`: pass the new settings through; no other behaviour change. `/health` is unchanged.
- `app/Sources/SloprFlow/Config.swift`: add the three keys to `defaults`, commented out, with a
  one-line comment each, in the style of the existing comments.

## Docs

- Top `README.md`, Config section: the new keys in the TOML block and a short paragraph on using
  your own prompt or model, with the two caveats: the built-in models are fine-tunes trained on
  one exact prompt, so a new prompt for them will likely clean up worse; and a prompt that is not
  a cleanup (translate, summarize, rewrite as an email) needs `safety_check = false`.
- `sidecar/README.md`, Config section and the `clean equals raw` sentence in `/transcribe`:
  same facts, in its terser style.
- Keep the repo's wording conventions: "hook" and "hook file", never "plugin".

## Tests

- Message building for each placement, for both built-in models' bytes (Utter's final newline
  kept; ReFyne's stripped, mocking the download), and for a custom `prompt_file`.
- Load errors: unknown model without `prompt_file`, bad `placement`, missing or empty
  `prompt_file`. The existing `test_unsupported_model_fails_at_load` changes to match the new
  message.
- `prompt_file` path resolution: `~`, relative, absolute.
- Config: the new keys' defaults and their type errors.
- Server: with `safety_check = false` an implausible candidate is kept and an empty one is not;
  with `true` today's behaviour holds.
- `uv run pytest -q && uv run ruff check . && uv run pyright` pass, and `app/test.sh` passes.

## Out of scope

- Any `[stt]` prompt, vocabulary or Parakeet booster.
- Configurable `is_plausible` thresholds; it is on or off.
- Templating inside the prompt file (no `{transcript}` placeholder).
