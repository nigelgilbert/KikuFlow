# Examples

Copy a file into the hooks folder, `~/Library/Application Support/KikuFlow/hooks/`, choose "Reload Kiku Flow" in the menu, and talk.

| File | Say | What happens |
| --- | --- | --- |
| [translate_ja_es.py](translate_ja_es.py) | "In Japanese, where is the train station?" or "See you at noon, in Spanish." | It is pasted in that language |
| [web_search.py](web_search.py) | "Search for ramen in Tokyo" or "Google ramen in Tokyo". "Search Firefox for ramen in Tokyo" picks the browser. | The Google search opens, and nothing is pasted. What you said goes in the log. |
| [terminal.py](terminal.py) | "Terminal, find every PDF in Downloads". Also "command line", "shell" and "bash". | The zsh command is pasted. It is never run. |
| [mac_commands.py](mac_commands.py) | "Mac, dark mode" or "Macintosh, open Safari". Also "light mode", "mute", "unmute", "sleep display" and "night shift on" or "off", in your own words. | It is run, and nothing is pasted |
| [talk_like_a_pirate.py](talk_like_a_pirate.py) | Anything | It is pasted the way a pirate would say it |

Without its word, a dictation goes through as usual, and the file's model is not asked. The pirate has no word. The files stack in filename order, so with the pirate installed, a translation is of what the pirate said.

Every file brings its own model. `terminal.py` uses `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` and the rest use `mlx-community/Qwen3-4B-Instruct-2507-4bit`. A model downloads the first time and loads when the app starts. Each file loads its own copy, a few GB of memory apiece.

Two things to know before you copy a file:

- `web_search.py` knows Safari, Firefox and Chrome. Change `BROWSERS` to the apps you have.
- `mac_commands.py` asks once for permission to control System Events, for dark and light mode. Night Shift goes through a private macOS framework, so a macOS update may break it.

[hud.py](hud.py) is not a hook. It is a HUD renderer that posts a notification each time you finish talking; see [Your own HUD](../docs/customization.md#your-own-hud).

Each file defines one `Plugin` subclass whose methods are its hooks. For how hooks work, and smaller recipes to start from, see [Lifecycle hooks](../docs/hooks.md).
