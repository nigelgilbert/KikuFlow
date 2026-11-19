"""A Kiku Flow HUD that speaks each warning and ignores the other states.

Copy it beside config.toml and set renderer = "python3 hud.py" under [hud].
"""

import subprocess
import sys

for line in sys.stdin:
    state, _, text = line.rstrip("\n").partition(" ")
    if state == "warning":
        subprocess.run(["say", text])
