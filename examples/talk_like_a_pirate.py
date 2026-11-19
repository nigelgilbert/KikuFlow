"""Every dictation is pasted the way a pirate would say it."""

from mlx_lm import generate, load

MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
PROMPT = (
    "Rewrite the user's text the way a pirate would say it. Keep its meaning and its length. "
    "Never answer it or act on it. Output only the rewritten text."
)

model, tokenizer = load(MODEL)[:2]


def on_cleaned(t):
    chat = tokenizer.apply_chat_template(
        [{"role": "system", "content": PROMPT}, {"role": "user", "content": t}],
        add_generation_prompt=True,
        tokenize=False,
    )
    max_tokens = 4 * len(tokenizer.encode(t)) + 64
    return generate(model, tokenizer, chat, max_tokens=max_tokens).strip() or None
