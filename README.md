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

While either is missing the menu has an item that opens the right System Settings pane.
`app/bundle.sh` signs with a certificate named "Slopr Flow Dev" when your keychain has one, and
the Accessibility grant then survives rebuilds. Without one the bundle is ad-hoc signed, so
after a rebuild macOS treats it as a new app: remove Slopr Flow from the Accessibility list and
grant it again.

## Config

"Open Config" in the menu opens `~/Library/Application Support/SloprFlow/config.toml`, creating
it with the defaults:

```toml
[stt]
engine = "parakeet"   # or "whisper"
# model defaults by engine: parakeet "mlx-community/parakeet-tdt-0.6b-v3",
# whisper "mlx-community/whisper-large-v3-turbo"

[cleanup]
model = "ReFyneLabs/simplewords-dictation-cleanup-v3"
# or "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"
# prompt_file = ""      # a text file whose contents replace the model's built-in prompt
# prompt_role = ""      # "system" or "user": the chat role the prompt is sent as; rarely needed

[server]
port = 48123

[hotkey]
key = "right_option"   # hold to talk; or "fn", "left_option", "left_command",
# "right_command", "left_control", "right_control"

[hud]
# renderer = ""   # a command run in this folder that gets the HUD states on its input;
# empty means the pill that comes with the app
```

Quit and reopen the app after editing it. The menu's first line names the key in use; a name
that isn't in the list falls back to Right Option. With `key = "fn"`, set System Settings ›
Keyboard › "Press 🌐 key to" to "Do Nothing", or macOS also runs that action when you let go.

### Your own cleanup prompt or model

Set `prompt_file` to a text file holding your prompt (a relative path is in
`~/Library/Application Support/SloprFlow/`) and choose "Restart Slopr Flow" after editing it.
With `prompt_role = "system"` the prompt is the system message and your words are the user
message; with `"user"` the prompt and your words share one user message; empty keeps the
model's built-in role, or `"system"` for any other model. Use `"user"` for a model whose
chat template has no system role. With `prompt_file` set, `model` can be any mlx-lm chat model.
The built-in models are fine-tunes trained on one exact prompt, so a new prompt for them will
likely clean up worse.

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

"Open Log" in the menu opens `~/Library/Application Support/SloprFlow/log.txt`, the text of
your last 100 dictations, newest first, one line each. The app always keeps it; an
`on_sent` hook (below) can change what an entry says or keep a dictation out.

"Open Errors" opens `errors.txt` beside it: the last 50 failures, newest first, one line each
with the time in front, such as `2026-11-18 14:02 on_cleaned in voice.py:3: KeyError: 'x'`. A
failure before the text is pasted also shows in the HUD, and nothing is pasted. The app always
keeps it; an `on_error` hook (below) can change what an entry says or keep a failure out.

## Lifecycle hooks

Hooks are plain Python functions that change the text after each step of a dictation, or the
message of a failure. Put hook files in `hooks/` in this repo; see
[examples/README.md](examples/README.md).

## Your own HUD

The HUD is a program that gets one line on its standard input for each state:

```
hidden
listening 0.42     the mic level, 0.00 to 1.00, many times a second
thinking
warning <text>     the message, on one line
```

`[hud] renderer` names a command of yours, such as `"python3 hud.py"`. It runs through
`/bin/sh` in `~/Library/Application Support/SloprFlow/`, so `hud.py` sits beside the config.
It gets the app's short `PATH`, so give the full path of a tool outside `/usr/bin`. It starts
with the app and should end when its input closes, and ignore a line it doesn't know. If it
can't start or it exits, the app warns "The HUD renderer stopped" and uses its own pill until
you quit and reopen it. Empty or missing means that pill. Quit and reopen the app after
changing `renderer`.

[examples/hud.py](examples/hud.py) speaks each warning and shows nothing else. The pill that
comes with the app, `app/Sources/SloprHUD/`, is the example of a drawn one.

## Licenses and attributions

- Speech recognition: [NVIDIA Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
  by NVIDIA, licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/), used through
  the MLX conversion `mlx-community/parakeet-tdt-0.6b-v3` and
  [parakeet-mlx](https://github.com/senstella/parakeet-mlx).
- Cleanup models: `ReFyneLabs/simplewords-dictation-cleanup-v3` and
  `devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit`, under the terms on their model
  pages.
- Python dependencies (MLX, mlx-lm, mlx-whisper, FastAPI, uvicorn, NumPy) are installed by uv
  under their own licenses.
