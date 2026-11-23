# Plan: plugins as the hook interface

## Goal

A hook file defines one or more `Plugin` subclasses whose methods are the hooks. The pipeline is unchanged: the same five hooks, the same return rules, the same filename order, the same error labels.

```python
from typing import override

from kiku_sidecar import Plugin


class Shout(Plugin):
    @override
    def on_cleaned(self, t: str) -> str:
        return t.upper()
```

Module-level `on_*` functions are no longer hooks. There is no adapter for the old form and no deprecation notice: the docs and examples move to plugins in the same change, and a new release carries it.

## Not changing

- The `hooks/` folder name and location, so the Swift app, `install.sh` and `app/bundle.sh` are untouched.
- What each hook receives and what its return means, including `on_done` returning a string that is not used.
- The labels in `errors.txt`, such as `on_cleaned in voice.py:3` and `hook file voice.py`.
- The pipeline order in `process` and `after_reply` in `sidecar/src/kiku_sidecar/server.py`.

## Design

1. **`Plugin` base class** in `sidecar/src/kiku_sidecar/lifecycle.py`, re-exported from `sidecar/src/kiku_sidecar/__init__.py`, which is empty today.
   - `on_transcribed`, `on_cleaned`, `on_sent` and `on_done` take a `str` and return it.
   - `on_error` takes the exception and returns it, which already means "pass" to `hook_message`.
   - Each method carries a docstring saying when it fires and what its return becomes, as the table in `docs/hooks.md` does.

2. **Loading.** `load_hooks` becomes `load_plugins` and returns a flat list of plugins, each paired with its file's path for the error label.
   - Run each `*.py` in filename order with `runpy.run_path`, as now.
   - Instantiate, with no arguments, every `Plugin` subclass defined in that file, in definition order.
   - Skip classes the file only imported, `Plugin` itself included. A class defined in the file has `__module__ == "<run_path>"`.
   - A failure in `__init__` gets the same `hook file voice.py` label as a failed import.
   - A missing directory gives an empty list.

3. **Firing.** `fire`, `fire_done` and `hook_message` loop over the list and call the method by name. The `Hooks` dict type and its `Any` callables go away, and so does `POINTS` unless something still needs it. The checks in `call` and `call_error` on what a hook returns stay.

4. **Server.** `Models.hooks` becomes `Models.plugins`, and the imports and call sites in `server.py` are renamed to match.

## Steps

1. Add `Plugin` and `load_plugins`, and rework `fire`, `fire_done`, `hook_message` and `report` to take the list.
2. Update `server.py`.
3. Rework `sidecar/tests/test_lifecycle.py`. The dict literals become small `Plugin` subclasses. New tests:
   - Defaults pass text and exceptions through.
   - Two plugins in one file run in definition order.
   - An imported subclass is not instantiated.
   - State on `self` persists between hooks.
   - A failing `__init__` is labelled `hook file <name>`.
   - A file with only module-level `on_*` functions loads no plugins.
4. Update `sidecar/tests/test_examples.py` to assert each docs block loads at least one plugin, and `sidecar/tests/test_server.py` for the rename.
5. Port the ten recipes in `docs/hooks.md`, where `global raw` becomes `self.raw`. Rewrite "Your first hook", the sentence about looking for five names, and the paragraph on module-level state. Module-level state still works and a model loaded at the top of a file stays loaded; say so.
6. Port the five hook files in `examples/`: `mac_commands.py`, `talk_like_a_pirate.py`, `terminal.py`, `translate_ja_es.py` and `web_search.py`. `hud.py` is not a hook file. `translate_ja_es.py` loses its `global language`.
7. Adjust wording in `README.md`, `sidecar/README.md`, `docs/customization.md` and `examples/README.md` where they describe writing a hook.
8. Add `examples/` to the pyright run, in `sidecar/pyproject.toml` or `.github/workflows/test.yml`, whichever runs it today, so the examples are checked against `Plugin`.
9. Run `ruff`, `pyright` and `pytest` in `sidecar/`.

## Acceptance

- `from kiku_sidecar import Plugin` works from a hook file.
- Every Python block in `docs/hooks.md` and every hook file in `examples/` is a `Plugin` subclass using `@override`, with no `global`.
- `ruff check`, `ruff format --check`, `pyright` (covering `examples/`) and `pytest` pass in `sidecar/`.
- No reference to `load_hooks` or the `Hooks` type remains.
- The Python follows `docs/pythonic.md`.
