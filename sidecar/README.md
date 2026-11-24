# Kiku Flow sidecar

Local HTTP server that turns dictated audio into raw and cleaned text. Listens on `127.0.0.1` on the port given at launch (see below). JSON responses.

## Install and launch

From the app bundle, keep `scripts/` and `sidecar/` side by side and run once per launch (idempotent, under a second when already installed; needs network the first time). `install.sh` runs it too, so an installed app starts with the engine in place:

```sh
/bin/sh <bundle>/scripts/bootstrap.sh
```

It uses the `uv` beside it, which `app/bundle.sh` copies into the bundle, or else the one on your PATH, and exits non-zero with a message on stderr if there is neither. It creates `~/Library/Application Support/KikuFlow/venv` with the pinned Python. Start the server as a child process, passing the port as the only argument:

```sh
"$HOME/Library/Application Support/KikuFlow/venv/bin/kiku-sidecar" 48123
```

The config is read only by the model loader, so a broken config shows up as a `/health` error instead of a crash. The process stays in the foreground, logs to stderr, and exits by itself within a second if its parent process dies. Kill it to stop it.

## Endpoints

### `GET /health`

Answers immediately, also while models load (first launch downloads several GB).

```json
{"ready": true, "error": null, "stt_engine": "parakeet",
 "stt_model": "mlx-community/parakeet-tdt-0.6b-v3",
 "cleanup_model": "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"}
```

- Loading: `ready` false, `error` null, model fields null. Keep polling.
- Load failed: `ready` false, `error` is a message (e.g. bad config, download failure, or a hook file that fails to import, as `hook file voice.py: ModuleNotFoundError: …`). Show it; the server stays up, fix the cause and restart it.

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

`clean` equals `raw` when the cleanup output is empty or nothing was said, unless the vocabulary or a hook changed it. Audio under 0.1 s returns empty strings. Paste `clean`.

A hook file defines subclasses of `kiku.Plugin`, and the sidecar makes one of each, with no arguments, when it loads the file. Their methods are the hooks, and one a plugin does not override passes its input on. Four lifecycle hooks take the text as a plain string and each returns the text, changed or not: `on_transcribed` after speech recognition and the vocabulary (the cleanup model gets its result), `on_cleaned` after the cleanup stage (`clean` is its result), then, once the response has been sent, `on_sent` (the log gets its result), the log and `on_done` (its result is not used). Those three do not delay the reply, but they run on the model thread, so a slow hook holds up the next dictation. `raw` is always the speech recognition output, before the vocabulary. Once the text is empty, nothing further runs, the log included. The log is always written, by the sidecar itself: the last 100 texts in `~/Library/Application Support/KikuFlow/log.txt`, newest first, one line each. Hook files are the `*.py` files in `~/Library/Application Support/KikuFlow/hooks/`, which a build from source links to `hooks/` in the repo unless the folder is already there. They load before the models, in filename order and then in the order each file defines its plugins. A file that fails to import, or a plugin whose `__init__` fails, fails the load. Examples: `docs/hooks.md`.

An exception from speech recognition, the vocabulary, the cleanup model, a hook or the log write is not caught and carried on: nothing after it runs. The sidecar adds a note to it naming where it came from (`speech recognition`, `vocabulary`, `cleanup model`, `log write`, or the hook as `on_cleaned in voice.py:3`) and the default message is `on_cleaned in voice.py:3: KeyError: 'x'`, on one line. A hook that returns anything but a string raises `TypeError: on_cleaned returned NoneType, not str`. `on_error(e)` hooks get the exception, in the same order; the first that returns a string decides the message, `""` means none, one that returns `e` passes to the next, and one that fails is skipped and recorded under its own default message. A return that is neither a string nor `e` is such a failure. The message goes into `~/Library/Application Support/KikuFlow/errors.txt`, the last 50, newest first, with the time in front, and the traceback to stderr. The app keeps stderr in `sidecar.log` beside it and empties that file when it starts. A failure after the response goes nowhere else. A model-load failure skips `on_error` and always goes into errors.txt.

Errors: `400` malformed audio; `500` a failure before the response, with the message as `detail` (`""` when `on_error` returned `""`); `503` models not loaded (`detail` holds the reason). Requests are processed one at a time; one sent while models load waits for them.

## Config

`~/Library/Application Support/KikuFlow/config.toml`, read once at launch. Missing file or keys use these defaults:

```toml
[stt]
engine = "parakeet"   # or "whisper" (mlx-whisper)
model = "mlx-community/parakeet-tdt-0.6b-v3"   # with "whisper": "mlx-community/whisper-large-v3-turbo"

[cleanup]
model = "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"
# or "ReFyneLabs/simplewords-dictation-cleanup-v3"
prompt_file = ""      # a text file whose contents replace the model's built-in prompt
prompt_role = ""      # "system" or "user": the chat role the prompt is sent as; rarely needed
```

The app reads `[server] port` and `[hotkey] key` from the same file; the sidecar ignores them.

## Vocabulary

`~/Library/Application Support/KikuFlow/vocabs.txt`, read at model load: one term per line, surrounding whitespace stripped, blank lines ignored; a missing file is no vocabulary. Between speech recognition and `on_transcribed`, each whole-word, case-insensitive match of a term, taken as literal text, is spelled as listed; of overlapping terms the longer wins. With `engine = "whisper"`, the terms joined with `, ` are also Whisper's `initial_prompt`. Words Parakeet hears as other words are not changed.

`prompt_file`: `~` expanded, relative to `~/Library/Application Support/KikuFlow/`, read at model load; missing or empty is a load error naming the path. `prompt_role`: `"system"` sends the prompt verbatim as the system turn and the transcript as the user turn; `"user"` sends one user turn, the stripped prompt, a blank line, the transcript; any other value is a load error. Empty means the model's built-in role (ReFyne `user`, Utter `system`), or `system` for any other model. A model whose chat template has no system role (Gemma 2, for one) fails to load with the template's error; set `prompt_role = "user"`. Any mlx-lm chat model works with `prompt_file`; an unknown model without it is a load error. The built-in models are fine-tunes trained on one exact prompt, so another prompt likely cleans up worse. Whatever the model returns is used; generation stops at 4x the input tokens plus 256.

The ReFyne cleanup model is a gated Hugging Face repo: it downloads only after the user accepts its terms on huggingface.co and logs in (`HF_TOKEN` in the sidecar's environment, or a token saved by `hf auth login`). Otherwise `/health` reports a `GatedRepoError`.

## Development

```sh
uv run pytest -q && uv run ruff check . && uv run pyright
uv run kiku-sidecar 48123
```
