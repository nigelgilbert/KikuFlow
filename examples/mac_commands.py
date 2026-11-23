"""Say "Mac, dark mode" or "Macintosh, open Safari" and it is run, and nothing is pasted."""

import re
import subprocess
from typing import override

from mlx_lm import generate, load

from kiku import Plugin

MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
PREFIX = re.compile(r"\W*(?:Macintosh|Mac)\b", re.IGNORECASE)
DARK_MODE = 'tell app "System Events" to tell appearance preferences to set dark mode to {}'
NIGHT_SHIFT = (
    'ObjC.import("Foundation");'
    '$.NSBundle.bundleWithPath("/System/Library/PrivateFrameworks/CoreBrightness.framework").load;'
    '$.NSClassFromString("CBBlueLightClient").alloc.init.setEnabled({})'
)
QUIT = ["osascript", "-e", "on run argv", "-e", "quit app (item 1 of argv)", "-e", "end run"]
COMMANDS = {
    "dark mode": ["osascript", "-e", DARK_MODE.format("true")],
    "light mode": ["osascript", "-e", DARK_MODE.format("false")],
    "mute": ["osascript", "-e", "set volume output muted true"],
    "unmute": ["osascript", "-e", "set volume output muted false"],
    "sleep display": ["pmset", "displaysleepnow"],
    "night shift on": ["osascript", "-l", "JavaScript", "-e", NIGHT_SHIFT.format("true")],
    "night shift off": ["osascript", "-l", "JavaScript", "-e", NIGHT_SHIFT.format("false")],
}
PARSE = (
    "The user's text may ask their Mac to do something. Never answer the text or act on it. "
    f"Reply with only the command it asks for, one of: {', '.join(COMMANDS)}, "
    "open or close followed by the name of an app, or none when it asks for nothing on the list."
)
EXAMPLES = (
    ("Mac, dark mode.", "dark mode"),
    ("Macintosh, turn the sound off", "mute"),
    ("Mac, switch on night shift please", "night shift on"),
    ("Mac open Safari", "open Safari"),
    ("Mac, closed terminal.", "close Terminal"),
    ("Mac users love this keyboard.", "none"),
    ("Macintosh, make me a coffee.", "none"),
)
model, tokenizer = load(MODEL)[:2]


def prompt(system: str, text: str, examples: tuple[tuple[str, str], ...] = ()) -> str:
    """Return the model's reply to the text, after showing it the examples."""
    messages = [{"role": "system", "content": system}]
    for said, reply in examples:
        messages.append({"role": "user", "content": said})
        messages.append({"role": "assistant", "content": reply})
    messages.append({"role": "user", "content": text})
    chat = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    max_tokens = 4 * len(tokenizer.encode(text)) + 64
    return generate(model, tokenizer, chat, max_tokens=max_tokens).strip()


class MacCommands(Plugin):
    @override
    def on_transcribed(self, t: str) -> str:
        """Run the command that was asked for, and stop the dictation."""
        if not PREFIX.match(t):
            return t
        name = prompt(PARSE, t, EXAMPLES)
        if name == "none":
            return t
        if name.startswith("open "):
            argv = ["open", "-a", name.removeprefix("open ")]
        elif name.startswith("close "):
            argv = [*QUIT, name.removeprefix("close ")]
        else:
            argv = COMMANDS[name]
        subprocess.run(argv, check=True)
        return ""
