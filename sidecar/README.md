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

Without the argument (run by hand) the port comes from `server.port` in the config. With it,
the config is read only by the model loader, so a broken config shows up as a `/health` error
instead of a crash. The process stays in the foreground, logs to stderr, and exits by itself
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
- Load failed: `ready` false, `error` is a message (e.g. bad config, download failure). Show
  it; the server stays up, fix the config and call `/reload`.
- `cleanup_model` is null when cleanup is disabled in config.

### `POST /transcribe?cleanup=true|false`

Body: one utterance, 16 kHz mono, either

- raw PCM: float32 little-endian samples, no header (what AVAudioEngine gives you), or
- a WAV file, 16-bit PCM. Detected by its `RIFF` header.

`cleanup` defaults to `true`. Response:

```json
{"raw": "Um, so we should meet Thursday. No, Friday.",
 "clean": "We should meet Friday.",
 "timings": {"stt_ms": 64, "cleanup_ms": 89}}
```

`clean` equals `raw` when cleanup is off (query or config), when the cleanup output fails the
safety check, or when nothing was said, unless a hook changed it. Audio under 0.1 s returns
empty strings. Paste `clean`.

Lifecycle hooks run on the text in between: `on_transcribed` after speech recognition (the
cleanup model gets its result), `on_cleaned` after the cleanup stage, also when cleanup is off,
and `on_logged` after the response has been sent, so it does not delay that reply (it runs on
the model thread, so a slow one holds up the next dictation). `raw` is always the speech
recognition output. Once the text is empty, no further hook runs. Hook files are the
`*.py` files in `src/slopr_sidecar/hooks/` (built-in) and in
`~/Library/Application Support/SloprFlow/hooks/`, where a file replaces the built-in of the
same name. They load with the models, so `/reload` re-reads them; one that fails to import is
skipped and does not set `/health`'s `error`. The built-in `log.py` keeps the last 100 texts in
`~/Library/Application Support/SloprFlow/log.txt`. Examples: `examples/README.md`.

Errors: `400` malformed audio, `503` models not loaded (`detail` holds the reason). Requests
are processed one at a time; one sent while models load waits for them.

### `POST /reload`

Re-reads `config.toml` and reloads the models in the background. Returns the `/health` body
(`ready` false); poll `/health` until ready. The port never changes without a restart.

## Config

`~/Library/Application Support/SloprFlow/config.toml`. Missing file or keys use these defaults:

```toml
[stt]
engine = "parakeet"   # or "whisper" (mlx-whisper)
model = "mlx-community/parakeet-tdt-0.6b-v3"   # with "whisper": "mlx-community/whisper-large-v3-turbo"

[cleanup]
enabled = true
model = "ReFyneLabs/simplewords-dictation-cleanup-v3"
# or "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"

[server]
port = 48123
```

The default cleanup model is a gated Hugging Face repo: it downloads only after the user
accepts its terms on huggingface.co and logs in (`HF_TOKEN` in the sidecar's environment, or
a token saved by `hf auth login`). Otherwise `/health` reports a `GatedRepoError`.

## Development

```sh
uv run pytest -q && uv run ruff check . && uv run pyright
uv run slopr-sidecar
```
