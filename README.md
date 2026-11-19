# Kiku Flow

*Kiku* (聞く): to listen.

Hold a key, talk, let go. Your words land in whatever app you're in.

It works like a Unix pipe: text in, text out, your Python in the middle.

| You say | It pastes |
| --- | --- |
| "Um, so we should meet Thursday. No, Friday." | We should meet Friday. |

Kiku Flow is yet another dictation app for Apple Silicon Macs.  It's fast and it runs entirely on your machine. NVIDIA Parakeet does the listening and a small language model does the tidying. 

No telemetry and nothing you say leaves your Mac.

## You can script it

Every dictation takes the same short trip, and the stops in brackets are yours:

```
mic → transcribe → [on_transcribed] → cleanup → [on_cleaned] → paste → [on_sent] → log → [on_done]
```

A hook is a Python function in a file in `hooks/`. It gets the text and returns the text. This one makes every dictation read like a chat message, with no capital at the start and no full stop at the end:

```python
def on_cleaned(t):
    t = t.removesuffix(".")
    return t[:1].lower() + t[1:]
```

That is the whole plugin system. A hook is plain Python, so it can call a second model or drive your Mac. The ones in [examples/](examples/) translate what you say, answer your questions and run commands by voice.

## Quick start

You need an Apple Silicon Mac on macOS 15 or later, Swift 6 (Xcode or the Command Line Tools) and [uv](https://docs.astral.sh/uv/).

```sh
brew install uv
app/bundle.sh
open "app/build/Kiku Flow.app"
```

The first launch installs its own Python and downloads the models, several GB.

1. Grant **Accessibility** when asked. The hotkey and the paste need it.
2. Hold Right Option. The first time, macOS asks for the **Microphone**; allow it and hold again.
3. Say something and let go.

The default cleanup model needs a free Hugging Face login. If the icon turns into a warning triangle, [the cleanup model](docs/customization.md#cleanup) has the two ways past it.

## Make it yours

- [Lifecycle hooks](docs/hooks.md): the pipeline, the hooks and a page of recipes.
- [Customization](docs/customization.md): the hotkey, the models, your own cleanup prompt, the log, your own HUD, and how the paste behaves.
- [examples/](examples/): hooks to copy into `hooks/` and talk to.

## Under the hood

`app/` is a small Swift menu-bar app that watches the key, records and pastes. `sidecar/` is the speech engine, a local Python server that transcribes and cleans up through MLX; [its README](sidecar/README.md) has the HTTP API. Tests are `app/test.sh` and, in `sidecar/`, `uv run pytest -q`.

## Licenses and attributions

- Speech recognition: [NVIDIA Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) by NVIDIA, licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/), used through the MLX conversion `mlx-community/parakeet-tdt-0.6b-v3` and [parakeet-mlx](https://github.com/senstella/parakeet-mlx).
- Cleanup models: `ReFyneLabs/simplewords-dictation-cleanup-v3` and `devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit`, under the terms on their model pages.
- Python dependencies (MLX, mlx-lm, mlx-whisper, FastAPI, uvicorn, NumPy) are installed by uv under their own licenses.
