"""Start with "terminal", "command line", "shell" or "bash" and the command is pasted, never run."""

import re
from typing import override

from mlx_lm import generate, load

from kiku_sidecar import Plugin

MODEL = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
WORDS = "terminal|command[- ]?line|shell|bash"
PREFIX = re.compile(rf"\W*(?:{WORDS})\b\W*(.+)", re.IGNORECASE | re.DOTALL)
PROMPT = (
    "Write the zsh command for macOS that does what the user asks, run from the folder they mean. "
    "Output only the command, on one line, with no code fence and no explanation."
)

model, tokenizer = load(MODEL)[:2]


class Terminal(Plugin):
    @override
    def on_cleaned(self, t: str) -> str:
        """Return the command that does what was asked, in place of the request."""
        said = PREFIX.match(t)
        if not said:
            return t
        messages = [{"role": "system", "content": PROMPT}, {"role": "user", "content": said[1]}]
        chat = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        reply = generate(model, tokenizer, chat, max_tokens=128)
        return reply.strip("` \n") or t
