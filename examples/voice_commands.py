"""Say "command open Safari" or "command dark mode" and it is run, and nothing is pasted."""

import re
import subprocess

PREFIX = re.compile(r"command\b\W*(.+?)\W*$", re.IGNORECASE | re.DOTALL)
DARK_MODE = (
    'tell app "System Events" to tell appearance preferences to set dark mode to not dark mode'
)
COMMANDS = {  # keys in lower case
    "dark mode": ["osascript", "-e", DARK_MODE],
    "mute": ["osascript", "-e", "set volume output muted true"],
    "unmute": ["osascript", "-e", "set volume output muted false"],
    "sleep display": ["pmset", "displaysleepnow"],
}


def on_transcribed(t):
    said = PREFIX.match(t)
    if not said:
        return None
    name = said[1].lower()
    if name.startswith("open "):
        argv = ["open", "-a", name.removeprefix("open ")]
    elif name in COMMANDS:
        argv = COMMANDS[name]
    else:
        raise ValueError(f"no command called {name!r}")
    subprocess.run(argv, check=True)
    return ""
