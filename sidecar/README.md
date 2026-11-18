# Slopr Flow sidecar

Local HTTP server that turns dictated audio into raw and cleaned text. Listens on
`127.0.0.1` on the port given at launch (see below). JSON responses.

## Install and launch

From the app bundle, keep `scripts/` and `sidecar/` side by side and run once per launch
(idempotent, under a second when already installed; needs network the first time):

```sh
/bin/sh <bundle>/scripts/bootstrap.sh
```

It exits non-zero with a message on stderr if `uv` is missing. It creates
`~/Library/Application Support/SloprFlow/venv` with the pinned Python. Start the server as a
child process, passing the port as the only argument:

```sh
"$HOME/Library/Application Support/SloprFlow/venv/bin/slopr-sidecar" 48123
```

The app first runs `slopr-config`, which prints the config as one line of JSON, and passes its
`port` to `slopr-sidecar`:

```sh
$ "$HOME/Library/Application Support/SloprFlow/venv/bin/slopr-config"
{"stt_engine": "parakeet", "stt_model": "mlx-community/parakeet-tdt-0.6b-v3", …, "port": 48123, "hotkey_key": "right_option"}
```

On a config it can't read (not valid TOML, or a value of the wrong type) it exits non-zero with
one line on stderr, such as `config port must be int, got '9000'` or
`config line 3: Expected '=' after a key in a key/value pair`. The app shows that line and does
not start the sidecar.

In `slopr-sidecar` the config is read only by the model loader, so a broken config shows up as a
`/health` error instead of a crash. The process stays in the foreground, logs to stderr, and exits by itself
within a second if its parent process dies. Kill it to stop it.

## Endpoints

### `GET /health`

Answers immediately, also while models load (first launch downloads several GB).

```json
{"ready": true, "error": null, "stt_engine": "parakeet",
 "stt_model": "mlx-community/parakeet-tdt-0.6b-v3",
 "cleanup_model": "ReFyneLabs/simplewords-dictation-cleanup-v3"}
```

- Loading: `ready` false, `error` null, model fields null. Keep polling.
- Load failed: `ready` false, `error` is a message (e.g. bad config, download failure, or a
  hook file that fails to import, as `hook file voice.py: ModuleNotFoundError: …`). Show it;
  the server stays up, fix the cause and restart it.

### `POST /transcribe`

Body: one utterance, 16 kHz mono, either

- raw PCM: float32 little-endian samples, no header (what AVAudioEngine gives you), or
- a WAV file, 16-bit PCM. Detected by its `RIFF` header.

Response:

```json
{"raw": "Um, so we should meet Thursday. No, Friday.",
 "clean": "We should meet Friday.",
 "timings": {"stt_ms": 64, "cleanup_ms": 89}}
```

`clean` equals `raw` when the cleanup output fails the safety check (or, with
`safety_check = false`, is empty), or when nothing was said, unless a hook changed it. Audio
under 0.1 s returns empty strings. Paste `clean`.

Four lifecycle hooks take the text as a plain string and return the text for the next phase:
`on_transcribed` after speech recognition (the cleanup model gets its result), `on_cleaned` after
the cleanup stage (`clean` is its result), then, once the response has been sent, `on_sent` (the log
gets its result), the log and `on_done`. Those three do not delay the reply, but they run on the
model thread, so a slow hook holds up the next dictation. `raw` is always the speech recognition
output. Once the text is empty, nothing further runs, the log included. The log is always written,
by the sidecar itself: the last 100 texts in `~/Library/Application Support/SloprFlow/log.txt`, one
line each. Hook files are the `*.py` files in `~/Library/Application Support/SloprFlow/hooks/`,
which `app/bundle.sh` links to `hooks/` in the repo. They load before the models, and one that
fails to import fails the load.
Examples: `examples/README.md`.

An exception from speech recognition, the cleanup model, a hook or the log write is not caught and
carried on: nothing after it runs. The sidecar adds a note to it naming where it came from (`speech
recognition`, `cleanup model`, `log write`, or the hook as `on_cleaned in voice.py:3`) and the
default message is `on_cleaned in voice.py:3: KeyError: 'x'`, on one line. A hook that returns
neither a string nor `None` raises `TypeError: on_cleaned returned dict, not str or None`.
`on_error(e)` hooks get the exception, in filename order; the first that returns a string decides
the message, `""` means none, and one that raises is skipped and recorded under its own default
message. The message goes into `~/Library/Application Support/SloprFlow/errors.txt`, the last 50
with the time in front, and the traceback to stderr. A failure after the response goes nowhere else.

Errors: `400` malformed audio; `500` a failure before the response, with the message as
`detail` (`""` when `on_error` returned `""`); `503` models not loaded (`detail` holds the
reason). Requests are processed one at a time; one sent while models load waits for them.

## Config

`~/Library/Application Support/SloprFlow/config.toml`, read once at launch. Missing file or keys
use these defaults:

```toml
[stt]
engine = "parakeet"   # or "whisper" (mlx-whisper)
model = "mlx-community/parakeet-tdt-0.6b-v3"   # with "whisper": "mlx-community/whisper-large-v3-turbo"

[cleanup]
model = "ReFyneLabs/simplewords-dictation-cleanup-v3"
# or "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"
prompt_file = ""      # a text file whose contents replace the model's built-in prompt
prompt_role = ""      # "system" or "user": the chat role the prompt is sent as; rarely needed
safety_check = true   # false keeps whatever the model returns

[server]
port = 48123

[hotkey]
key = "right_option"
```

`slopr-config` prints `[server] port` and `[hotkey] key` for the app; the sidecar itself doesn't
use them and takes the port as its argument. `key` is not checked here; the app falls back to
Right Option for a name it doesn't know.

`prompt_file`: `~` expanded, relative to `~/Library/Application Support/SloprFlow/`, read at
model load; missing or empty is a load error naming the path.
`prompt_role`: `"system"` sends the prompt verbatim as the system turn and the transcript as the
user turn; `"user"` sends one user turn, the stripped prompt, a blank line, the transcript; any
other value is a load error. Empty means the model's built-in role (ReFyne `user`, Utter
`system`), or `system` for any other model. A model whose chat template has no system role
(Gemma 2, for one) fails to load with the template's error; set `prompt_role = "user"`. Any mlx-lm
chat model works with `prompt_file`; an unknown model without it is a load error. The built-in
models are fine-tunes trained on one exact prompt, so another prompt likely cleans up worse.
`safety_check = false` uses any non-empty output and raises the generation cap from 2x to 4x the
input tokens (plus 256), which a prompt that is not a cleanup (translate, summarize, email)
needs.

The default cleanup model is a gated Hugging Face repo: it downloads only after the user
accepts its terms on huggingface.co and logs in (`HF_TOKEN` in the sidecar's environment, or
a token saved by `hf auth login`). Otherwise `/health` reports a `GatedRepoError`.

## Development

```sh
uv run pytest -q && uv run ruff check . && uv run pyright
uv run slopr-sidecar 48123
```
