# Factory report: feature/plugins, run 1

Work file: `docs/plugin-plan.md`. Base commit: `dd8acf3`. Reviews: 1. Adversary: sol.

## Work items

| Item | What landed | Commit |
| --- | --- | --- |
| 1. `Plugin` and `load_plugins` | `Plugin` base class with pass-through defaults, re-exported from `kiku_sidecar`. `load_plugins` returns `(path, plugin)` pairs. `fire`, `fire_done`, `hook_message` and `report` take the list. `Hooks`, `POINTS` and `Any` are gone. | `b9901d8` |
| 2. Server | `Models.plugins`, with imports and call sites renamed. Pipeline order unchanged. | `b9901d8` |
| 3. `test_lifecycle.py` | Rewritten around `Plugin` subclasses, with the six new tests. | `b9901d8` |
| 4. `test_examples.py`, `test_server.py` | Docs blocks must load a plugin. Server tests write plugin files. | `b9901d8` |
| 5. `docs/hooks.md` | Ten recipes ported with `@override` and no `global`. Prose rewritten. | `b9901d8` |
| 6. Examples | Five hook files ported. `hud.py` untouched. | `55b0e9e` |
| 7. Wording | `README.md`, `sidecar/README.md`, `docs/customization.md`, `examples/README.md`. | `3141c50` |
| 8. Pyright covers `examples/` | `include` in `sidecar/pyproject.toml`. | `5170a2d` |
| 9. Final checks | See Tests. | |

Items 1 to 5 share a commit because `test_examples.py` loads the blocks in `docs/hooks.md`, so the code, tests and docs only pass together.

## Review 1: trimmed list

Range `dd8acf3..5170a2d`. Candidates: 15. Kept: 7 (0 fix, 7 nit). Adversary: sol. Exchanges: 1.

### Fix

None.

### Nit

1. **De-duplicate aliased plugin classes.** `sidecar/src/kiku_sidecar/lifecycle.py:142-148`. A class bound to two names (`Default = Shout`) is instantiated twice. Fix: return each class once in first-seen order, e.g. `list(dict.fromkeys(classes))`. Confidence: medium.
2. **Docs-block test accepts a plugin that overrides nothing.** `sidecar/tests/test_examples.py:19`. It passes for a recipe with a misspelt hook. Fix: also assert that some loaded plugin overrides one of the five hooks. Confidence: high.
3. **"Runs once, when the app starts" leaves out reload.** `docs/hooks.md:58`. Fix: "A file runs when the app starts or reloads, and its plugins are made then." Confidence: high.
4. **`fire` takes any string as the hook name.** `sidecar/src/kiku_sidecar/lifecycle.py:180`. Fix: `point: Literal["on_transcribed", "on_cleaned", "on_sent"]`. Confidence: medium.
5. **Imported-subclass test leaves `shared` in `sys.modules`.** `sidecar/tests/test_lifecycle.py:105-111`. Fix: a module name nothing else can collide with, or pop it in a `finally`. Confidence: high.
6. **`Empty` docstring overstates what it does.** `sidecar/tests/test_lifecycle.py:48`. Fix: "Stop the dictation at on_transcribed, and return an empty string from on_done." Confidence: high.
7. **`load_plugins` docstring omits the path pairing.** `sidecar/src/kiku_sidecar/lifecycle.py:152`. Fix: "Return each plugin in every *.py in `directory` with its file's path, in filename order." Confidence: high.

### Wontfix

- Error for a file with only module-level `on_*` functions: contradicts the plan's "no adapter and no deprecation notice".
- Intermediate base classes are instantiated: the plan and `docs/hooks.md` say every subclass the file defines is made; a shared base can be imported.
- CI does not run pyright: plan step 8 is met through `pyproject.toml`; CI never ran pyright before.
- `translate_ja_es.py` parsing can raise: pre-existing, only re-indented here.
- `mac_commands.py` `KeyError` on an unknown command: pre-existing, and the proposed fix changes behaviour.
- `on_error` docstring does not list failure sources: it matches the docs table.
- `HEADER` and `plugin_file` duplicated in two test files: six lines, no rule against it.
- README `ChatVoice` block is untested and worded differently: same behaviour, and the gap predates the range.

### Split

None.

## Fix pass 1

Pass base `2335c09`. All seven nits were folded in, with no pushback.

| Item | Result | Commit |
| --- | --- | --- |
| 1. De-duplicate aliased plugin classes | Folded in, with a new test for `Alias = P`. | `e910dc1` |
| 2. Docs-block test accepts a plugin that overrides nothing | Folded in: some loaded plugin must override a hook. | `b907108` |
| 3. "Runs once" leaves out reload | Folded in. | `4ec41bf` |
| 4. `fire` takes any string | Folded in as `type TextPoint = Literal[...]`. `call` keeps `str` because it also handles `on_done`. | `e910dc1` |
| 5. `shared` left in `sys.modules` | Folded in with a module name nothing else imports. | `b907108` |
| 6. `Empty` docstring | Folded in. | `b907108` |
| 7. `load_plugins` docstring | Folded in. | `e910dc1` |

## Open items

- The gitignored local `hooks/` folder, which the installed app's hooks folder links to, still holds old-style `mac_commands.py`, `terminal.py` and `web_search.py`. They load no plugins on this branch until they are replaced with the ported files in `examples/`.
- CI runs only pytest. Pyright, which now covers `examples/`, runs locally.

## Tests

From `sidecar/`, at `4ec41bf`:

- `uv run ruff check . ../examples`: all checks passed
- `uv run ruff format --check . ../examples`: 21 files already formatted
- `uv run pyright`: 0 errors
- `uv run pytest -q`: 111 passed

## PR feedback

Four nits from a later review of the PR, with the user's read.

| Item | Result | Commit |
| --- | --- | --- |
| 1. Old-style hook files load silently and do nothing (`lifecycle.py`, `load_plugins`) | Struck by the user. The plan's "no adapter and no deprecation notice" stands. | |
| 2. Unguarded parse of the model reply (`examples/translate_ja_es.py:61`) | Fixed: a reply that is not the expected JSON leaves the text as it was. | `2a1594c` |
| 3. The vocabulary recipe's hook reads from the inside out (`docs/hooks.md:90`) | Fixed: the lambda is now a named helper, `corrected`. | `2a1594c` |
| 4. Recipe hooks have no docstrings (`docs/hooks.md`, `README.md`) | Folded in as one line per hook. | `2a1594c` |

Left as it was: in `translate_ja_es.py`, the `re.split` after the parse still raises when the language the model names is not in the text word for word. It was outside item 2.

Checks at `2a1594c`, from `sidecar/`: ruff clean, pyright 0 errors, pytest 111 passed.
