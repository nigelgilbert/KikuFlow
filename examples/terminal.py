"""Start with "terminal", "command line", "shell" or "bash" and the command is pasted, never run."""

import re
from typing import override

from kiku import Plugin, load_model

MODEL = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
WORDS = "terminal|command[- ]?line|shell|bash"
PREFIX = re.compile(rf"\W*(?:{WORDS})\b\W*(.+)", re.IGNORECASE | re.DOTALL)
PROMPT = (
    "Write the zsh command for macOS that does what the user asks, run from the folder they mean. "
    "Output only the command, on one line, with no code fence and no explanation."
)


class Terminal(Plugin):
    def __init__(self) -> None:
        self.model = load_model(MODEL)

    @override
    def on_cleaned(self, t: str) -> str:
        """Return the command that does what was asked, in place of the request."""
        said = PREFIX.match(t)
        if not said:
            return t
        reply = self.model.prompt(PROMPT, said[1])
        return reply.strip("` \n") or t
