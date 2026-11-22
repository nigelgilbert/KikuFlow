"""Start with "shell" and the command that does what you said is pasted. It is never run."""

import re

from mlx_lm import generate, load

MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
PREFIX = re.compile(r"terminal\b\W*(.+)", re.IGNORECASE | re.DOTALL)
PROMPT = (
    "Write the zsh command for macOS that does what the user asks, run from the folder they mean. "
    "Output only the command, on one line, with no code fence and no explanation."
)

model, tokenizer = load(MODEL)[:2]
wanted = False


def on_transcribed(t):
    """Take "shell" off the front, so the cleanup model sees only the request."""
    global wanted
    said = PREFIX.match(t)
    wanted = bool(said)
    return said[1] if said else t


def on_cleaned(t):
    if not wanted:
        return t
    chat = tokenizer.apply_chat_template(
        [{"role": "system", "content": PROMPT}, {"role": "user", "content": t}],
        add_generation_prompt=True,
        tokenize=False,
    )
    return generate(model, tokenizer, chat, max_tokens=128).strip() or t
