"""A Kiku Flow HUD that posts a notification each time you finish talking."""

import subprocess
import sys

for line in sys.stdin:
    if line.strip() == "thinking":
        subprocess.run(["osascript", "-e", 'display notification "Got it" with title "Kiku Flow"'])
