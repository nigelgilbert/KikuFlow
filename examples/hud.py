"""A Kiku Flow HUD that posts a notification each time you finish talking, and draws nothing.

Copy it beside config.toml and set renderer = "python3 hud.py" under [hud].
"""

import subprocess
import sys

for line in sys.stdin:
    if line.strip() == "thinking":
        subprocess.run(["osascript", "-e", 'display notification "Got it" with title "Kiku Flow"'])
