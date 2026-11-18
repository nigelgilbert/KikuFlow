# Plan: one config parser

Starts from `main` at `01d816e`. Today `config.toml` is parsed twice. The sidecar reads it with
`tomllib`, and the app reads `[server] port` and `[hotkey] key` with a hand-written reader in
`Config.swift` that knows only flat `key = value` lines. The two can disagree about a file that
is valid TOML, and a file that `tomllib` rejects still gives the app a port and a key.

## Rules

- **Python is the only parser.** The app no longer reads `config.toml` itself.
- **The app asks for the config once per launch**, by running a small command from the venv
  that prints it as JSON.
- **A broken config is loud in the app.** The menu shows the error and the sidecar is not
  started.

## Sidecar

- `Config` gains `hotkey_key: str = "right_option"`, read from `[hotkey] key` and type-checked
  like the other fields. It keeps `port`. Python does not check the key's name; the app owns the
  list of names.
- `config.py` gets `main()`, which prints `json.dumps(dataclasses.asdict(load_config()))` on one
  line. A failure is not caught: the traceback goes to stderr and the exit status is not zero.
- `pyproject.toml` gets the script `slopr-config = "slopr_sidecar.config:main"`.
  `scripts/bootstrap.sh` already reinstalls the package, so the command is in the venv after the
  next launch.
- `slopr_sidecar.config` keeps importing only the standard library, so the command starts fast.
- `slopr-sidecar` and how it gets its port are not touched.

## App

- Remove the TOML reader from `Config.swift`: `text`, `port`, `hotkey`, `port(in:)`,
  `hotkey(in:)` and `value(_:section:in:)`. `Config.defaults`, the paths and the `open` helpers
  stay.
- After `bootstrap.sh` has succeeded and before the sidecar is launched, the app runs
  `venv/bin/slopr-config` and decodes `port` and `hotkey_key` from its output.
  - On success it launches the sidecar with that port and starts the hotkey with that key.
  - On failure the status is `.failed` with the last line the command wrote to stderr, such as
    `TypeError: config port must be int, got '9000'`, and the sidecar is not launched.
- A key name that is not in `Hotkey.Key.named` still falls back to Right Option.
- The hotkey now starts once the config has been read, not at launch. On a first launch that
  means after the install. The Accessibility prompt stays at launch.
- Reuse what `Sidecar.bootstrap()` already does to run a process and take the last stderr line.
  Do not add a second copy of it.

## Docs

- `sidecar/README.md`: add `slopr-config` next to the launch instructions, with its output and
  what a failure looks like, and add `[hotkey] key` to the config block.
- Top `README.md`: in the Config section, say that a config the app can't read shows its error
  in the menu. Nothing else changes there.

## Tests

- Python:
  - `[hotkey] key = "fn"` is read, and the default is `right_option`.
  - `[hotkey] key = 3` raises the `TypeError` naming `hotkey_key`.
  - `main()` prints one line of JSON holding `port` and `hotkey_key` from a config file.
  - `main()` on a file that is not valid TOML raises.
- Swift: replace the four tests of the removed reader with
  - decoding the command's JSON gives the port and the key;
  - an unknown key name gives Right Option.
- `uv run pytest -q && uv run ruff check . && uv run pyright` and `app/test.sh` pass.

## Out of scope

- Making an unknown hotkey name an error.
- Any change to `Config.defaults`, the config keys or their defaults.
- PR #8 (`cleanup/tidy`), which is open and removes `port` from the Python `Config`. This plan
  needs `port` there, so whichever of the two merges second has to keep it.
