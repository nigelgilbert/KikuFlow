"""Say "Mac, dark mode" or "Macintosh, open Safari" and it is run, and nothing is pasted."""

import re
import subprocess
from typing import override

from kiku import Plugin, load_model

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


class MacCommands(Plugin):
    def __init__(self) -> None:
        self.model = load_model(MODEL)

    @override
    def on_transcribed(self, t: str) -> str:
        """Run the command that was asked for, and stop the dictation."""
        if not PREFIX.match(t):
            return t
        name = self.model.prompt(PARSE, t, EXAMPLES)
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
