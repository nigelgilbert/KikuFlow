# Customization

There are four things to change, from least to most effort: the config file, the cleanup prompt, hooks and the HUD.

Everything lives in the Kiku Flow folder, `~/Library/Application Support/KikuFlow/`:

| File | What it is |
| --- | --- |
| `config.toml` | The settings below |
| `hooks/` | Your [hook files](hooks.md) |
| `log.txt` | Your last 100 dictations |
| `errors.txt` | The last 50 failures |
| `sidecar.log` | The speech engine's error output since the app started |
| `venv/` | The speech engine's Python, re-synced at every launch |

## The config file

"Open Config" in the menu opens `config.toml`. These are the defaults:

```toml
[hotkey]
key = "right_option" # the key you hold to talk

[stt]
engine = "parakeet" # or "whisper"

[cleanup]
model = "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit" # or "ReFyneLabs/simplewords-dictation-cleanup-v3"

[hud]
renderer = "" # your custom HUD

[server]
port = 48123 # speech engine port
```

A missing key uses its default, and each section below covers one of them. Choose "Reload Kiku Flow" after any edit.

## The hotkey

`[hotkey] key` is the key you hold to talk: `right_option`, `left_option`, `right_command`, `left_command`, `right_control`, `left_control` or `fn`. The menu's first line names the key in use, and a name that isn't in the list falls back to Right Option.

With `key = "fn"`, set System Settings › Keyboard › "Press 🌐 key to" to "Do Nothing", or macOS also runs that action when you let go.

## The models

### Speech recognition

`[stt] engine` is `"parakeet"` or `"whisper"`. Each has a default model, so changing only the engine works. `[stt] model` takes any Hugging Face repo the engine can load, through [parakeet-mlx](https://github.com/senstella/parakeet-mlx) or [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper).

### Cleanup

`[cleanup] model` is the model that turns what you said into what you meant. Two come ready to use:

- `devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit`, the default.
- `ReFyneLabs/simplewords-dictation-cleanup-v3`.

The second is gated on Hugging Face. Before you set `model` to it, accept the terms on [the model's page](https://huggingface.co/ReFyneLabs/simplewords-dictation-cleanup-v3) and log in with `~/Library/Application\ Support/KikuFlow/venv/bin/hf auth login`, or `hf auth login` if you have the CLI. Without that, the reload stops at a warning triangle, and "Open Errors" says `Access to model … is restricted`.

`HF_TOKEN` works in place of a login only when the app is started from a shell that has it set, which a launch from Finder isn't.

## Your own cleanup prompt

The cleanup step is a chat model with a prompt, and you can replace both.

Write your prompt in a text file and point `[cleanup] prompt_file` at it. A relative path starts at the Kiku Flow folder, and `~` works. Reload after editing the file.

With `prompt_file` set, `model` can be any [mlx-lm](https://github.com/ml-explore/mlx-lm) chat model. The two built-in models are fine-tunes trained on one exact prompt, so with a new prompt they will likely clean up worse; a general chat model is the better partner for a prompt of your own.

`prompt_role` says how the prompt is sent:

| `prompt_role` | What the model gets |
| --- | --- |
| `"system"` | Your prompt as the system message, your words as the user message |
| `"user"` | One user message: your prompt, a blank line, your words |
| empty | The built-in model's own role, or `"system"` for any other model |

Use `"user"` for a model whose chat template has no system role.

Whatever the model returns is pasted, so the prompt should end by asking for the text and nothing else. A reply is cut off at four times the length of what you said, plus 256 tokens.

A prompt changes what the cleanup does. To keep the cleanup and add a step after it, write a hook.

## Hooks

A hook is a method of a plugin, a Python class in a file in `hooks/`, that changes the text at one point in a dictation. Hooks can fix vocabulary, translate, run commands, and choose what is logged and what an error says. [Lifecycle hooks](hooks.md) has all of it.

## Your own HUD

The HUD is the pill that shows the mic level while you talk. It is a separate program, and you can swap in one of yours. A HUD gets one line on its standard input for each state:

```
hidden
listening 0.42     the mic level, 0.00 to 1.00, many times a second
thinking
warning <text>     a message of up to 120 characters, on one line
```

What it does with them is up to it. This one, [examples/hud.py](../examples/hud.py), draws nothing and posts a notification each time you finish talking:

```python
import subprocess
import sys

for line in sys.stdin:
    if line.strip() == "thinking":
        subprocess.run(["osascript", "-e", 'display notification "Got it" with title "Kiku Flow"'])
```

To use it, copy `hud.py` beside `config.toml`, set `[hud] renderer = "python3 hud.py"` and reload.

The rules for a renderer:

- The command runs through `/bin/sh` in the Kiku Flow folder, with the app's short `PATH`. Give the full path of any tool outside `/usr/bin`.
- It starts with the app and should exit when its input closes.
- It should ignore a line it doesn't know.
- If it reads too slowly it misses lines. The app never waits for it.
- If it can't start, or it exits, the app warns "The HUD renderer stopped" and uses its own pill until you reload.

The pill that comes with the app, `app/Sources/KikuHUD/main.swift`, is the example of a drawn one.

## The log and the errors

"Open Log" in the menu opens `log.txt`: the text of your last 100 dictations, newest first. There is no setting to turn it off, but an [`on_sent` hook](hooks.md#choose-what-goes-in-the-log) can change what an entry says or keep a dictation out.

"Open Errors" opens `errors.txt`: the last 50 failures, newest first, each with the time in front:

```
2026-11-18 14:02 on_cleaned in voice.py:3: KeyError: 'x'
```

A failure before the paste also shows in the HUD, and nothing is pasted. An [`on_error` hook](hooks.md#on_error) can change what an entry says or keep a failure out, except for the models failing to load and the engine crashing, which always go in. A run of crashes is recorded once.

For a traceback, look in `sidecar.log`.

## Paste and permissions

Nothing here is a setting, but it is what the app does:

- After a paste into a text field, your previous clipboard comes back. When no text field has focus, the text stays on the clipboard for you to paste. Apps that don't report their text fields to Accessibility, some Electron apps among them, count as no text field.
- The paste sends ⌘ and the key in the V position of a US layout, so on a layout like Dvorak it may not be ⌘V.
- While a permission is missing, the menu has an item that opens the right System Settings pane.
- An update through the install script keeps the Accessibility grant. An app you build yourself is a new app to macOS after every build: remove Kiku Flow from the Accessibility list and grant it again. To keep the grant across builds, run `app/dev-cert.sh` once. It puts a "Kiku Flow Dev" certificate of your own in your keychain. `app/bundle.sh` then signs with it, and your builds share one grant, apart from the installed app's.

## The port

The app talks to its speech engine on `127.0.0.1` port `48123`. If something else on your Mac has that port, change `[server] port`.
