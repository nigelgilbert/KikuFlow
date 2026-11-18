# Slopr Flow

Hold-to-talk dictation for Apple Silicon Macs that runs entirely on your machine. Hold Right
Option (or the key you pick in the config), speak, let go, and the cleaned-up text is pasted
into whatever app has focus.

It is a small menu-bar app (`app/`, Swift) driving a local Python server (`sidecar/`) that
transcribes with NVIDIA Parakeet and tidies the text with a small fine-tuned LLM, both through
MLX. No cloud, no account.

## Requirements

- An Apple Silicon Mac on macOS 15 or later.
- [uv](https://docs.astral.sh/uv/) (`brew install uv`). On first launch the app uses it to
  install a pinned Python and the sidecar into `~/Library/Application Support/SloprFlow/venv`.
  The first launch also downloads the models, several GB.
- To build: Swift 6 (Xcode or the Command Line Tools).

## Build and run

```sh
app/bundle.sh                # builds app/build/Slopr Flow.app
open "app/build/Slopr Flow.app"
```

Tests: `app/test.sh`. The menu bar icon shows the state: hourglass while installing or loading
models, microphone when ready, waveform while listening, ellipsis while transcribing, a warning
triangle when the models failed to load (the menu shows the error).

## Permissions

- **Accessibility**, asked for at launch: the hotkey and the ⌘V paste need it.
  The hotkey starts working as soon as it's granted. If paste can't be sent, the text stays on
  the clipboard. The paste sends the key in the V position of a US layout, so on layouts like
  Dvorak it may not be ⌘V.
- **Microphone**, asked for the first time you hold the key.

While either is missing the menu has an item that opens the right System Settings pane. The
bundle is ad-hoc signed, so after a rebuild macOS treats it as a new app: remove Slopr Flow
from the Accessibility list and grant it again.

## Config

"Open Config…" in the menu opens `~/Library/Application Support/SloprFlow/config.toml`, creating
it with the defaults:

```toml
[stt]
engine = "parakeet"   # or "whisper"
# model defaults by engine: parakeet "mlx-community/parakeet-tdt-0.6b-v3",
# whisper "mlx-community/whisper-large-v3-turbo"

[cleanup]
enabled = true
model = "ReFyneLabs/simplewords-dictation-cleanup-v3"
# or "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"

[server]
port = 48123

[hotkey]
key = "right_option"   # hold to talk; or "fn", "left_option", "left_command",
# "right_command", "left_control", "right_control"
```

Quit and reopen the app after editing it. The menu's first line names the key in use; a name
that isn't in the list falls back to Right Option. With `key = "fn"`, set System Settings ›
Keyboard › "Press 🌐 key to" to "Do Nothing", or macOS also runs that action when you let go.
 "Clean Up Text" in the menu turns the cleanup pass off
and on without reloading anything.

### The default cleanup model is gated

`ReFyneLabs/simplewords-dictation-cleanup-v3` downloads only after you accept its terms on
[its Hugging Face page](https://huggingface.co/ReFyneLabs/simplewords-dictation-cleanup-v3) and
log in. Until then the menu shows `Access to model … is restricted`. Either:

- accept the terms, then log in with a token, which the sidecar picks up from where `hf` saves
  it:
  `~/Library/Application\ Support/SloprFlow/venv/bin/hf auth login` (or `hf auth login` if you
  have the CLI). `HF_TOKEN` works too, but only if it is in the environment the app is launched
  from, which Finder's isn't. Or
- set `[cleanup] model = "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"`, which is
  not gated.

## Log

"Open Log…" in the menu opens `~/Library/Application Support/SloprFlow/log.txt`, the text of
your last 100 dictations, oldest first, one paragraph each.

## Lifecycle hooks

The text passes through three hooks you can write in plain Python: `on_transcribed` after speech
recognition, `on_cleaned` after the cleanup model, `on_done` once the text has been sent to be
pasted. Put hook files in `~/Library/Application Support/SloprFlow/hooks/`, a folder you create,
and choose "Restart Slopr Flow". The log above is the built-in `log.py` hook file; a `log.py` of
your own replaces it. See [examples/README.md](examples/README.md) for vocabulary fixes, a
different voice and a different log.

## Licenses and attributions

- Speech recognition: [NVIDIA Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
  by NVIDIA, licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/), used through
  the MLX conversion `mlx-community/parakeet-tdt-0.6b-v3` and
  [parakeet-mlx](https://github.com/senstella/parakeet-mlx). Also shown in the app's About panel.
- Cleanup models: `ReFyneLabs/simplewords-dictation-cleanup-v3` and
  `devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit`, under the terms on their model
  pages.
- Python dependencies (MLX, mlx-lm, mlx-whisper, FastAPI, uvicorn, NumPy) are installed by uv
  under their own licenses.
