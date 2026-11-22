"""Start with "question" and the answer is pasted instead of what you said."""

import re

from mlx_lm import generate, load

MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
PREFIX = re.compile(r"question\b\W*(.+)", re.IGNORECASE | re.DOTALL)
PROMPT = "Answer the user's question in one or two sentences. Output only the answer."

model, tokenizer = load(MODEL)[:2]
asking = False


def on_transcribed(t):
    """Take "question" off the front, so the cleanup model sees only the question."""
    global asking
    said = PREFIX.match(t)
    asking = bool(said)
    return said[1] if said else t


def on_cleaned(t):
    if not asking:
        return t
    chat = tokenizer.apply_chat_template(
        [{"role": "system", "content": PROMPT}, {"role": "user", "content": t}],
        add_generation_prompt=True,
        tokenize=False,
    )
    reply = generate(model, tokenizer, chat, max_tokens=256).strip()
    return reply or t
