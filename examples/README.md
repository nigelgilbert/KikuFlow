# Examples

Copy a file into `hooks/`, choose "Reload Kiku Flow" in the menu, and talk.

| File | Say | What happens |
| --- | --- | --- |
| [translate.py](translate.py) | "In Japanese, where is the train station?" Also French, German, Hindi and Spanish. | It is pasted in that language |
| [ask.py](ask.py) | "Question, how tall is Mount Fuji?" | The answer is pasted instead of the question |
| [terminal.py](terminal.py) | "Terminal, find every PDF in Downloads" | The zsh command is pasted. It is never run. |
| [voice_commands.py](voice_commands.py) | "Command, open Safari". Also "dark mode", "mute", "unmute" and "sleep display". | It is run, and nothing is pasted |
| [talk_like_a_pirate.py](talk_like_a_pirate.py) | Anything | It is pasted the way a pirate would say it |

Without the opening word, a dictation goes through as usual. The pirate has no opening word. The files stack in filename order, so with the pirate installed, the answers to your questions come back in pirate.

All but `voice_commands.py` bring their own model, `mlx-community/Qwen3-4B-Instruct-2507-4bit`. It downloads the first time and loads when the app starts. Each file loads its own copy, a few GB of memory apiece.

[hud.py](hud.py) is not a hook. It is a HUD renderer that posts a notification each time you finish talking; see [Your own HUD](../docs/customization.md#your-own-hud).

For how hooks work, and smaller recipes to start from, see [Lifecycle hooks](../docs/hooks.md).
