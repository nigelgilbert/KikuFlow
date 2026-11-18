"""LLM cleanup of the raw transcript, and a safety check against the model going off-script."""

import re
from collections.abc import Callable
from pathlib import Path

from huggingface_hub import hf_hub_download
from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

type Cleaner = Callable[[str], str]
type Messages = list[dict[str, str]]


def _prompt(model: str) -> Callable[[str], Messages]:
    """Each supported model was trained on one exact prompt shape."""
    match model:
        case "ReFyneLabs/simplewords-dictation-cleanup-v3":
            # Frozen prompt shipped in the model repo; one user turn, no system role.
            path = hf_hub_download(model, "system_v2.txt")
            system = Path(path).read_text(encoding="utf-8").strip()
            return lambda raw: [{"role": "user", "content": f"{system}\n\n{raw}"}]
        case "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit":
            # Utter's prompt, byte for byte with its final newline, as the system turn. The MLX
            # repo doesn't ship it; utter_system.txt is the "System prompt" block of the model
            # card at hpal007/utter-dictation-cleanup-GGUF@68bbbf5589c85cbb18818c3a0609cfc90eb63dd5.
            system = Path(__file__).with_name("utter_system.txt").read_text(encoding="utf-8")
            return lambda raw: [
                {"role": "system", "content": system},
                {"role": "user", "content": raw},
            ]
        case _:
            raise ValueError(f"unsupported cleanup.model {model!r}")


def load_cleaner(model_name: str) -> Cleaner:
    messages = _prompt(model_name)
    model, tokenizer = load(model_name)[:2]
    greedy = make_sampler(temp=0.0)

    def clean(raw: str) -> str:
        prompt = tokenizer.apply_chat_template(
            messages(raw), add_generation_prompt=True, enable_thinking=False, tokenize=False
        )
        # Output longer than twice the input fails is_plausible anyway.
        max_tokens = 2 * len(tokenizer.encode(raw)) + 16
        return generate(model, tokenizer, prompt, max_tokens=max_tokens, sampler=greedy).strip()

    return clean


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def is_plausible(raw: str, clean: str) -> bool:
    """Whether `clean` looks like a cleanup of `raw` rather than an answer, a rewrite or nothing."""
    raw_words, clean_words = _words(raw), _words(clean)
    if not raw_words or not clean_words:
        return False
    if not 0.25 <= len(clean_words) / len(raw_words) <= 2.0:
        return False
    known = set(raw_words)
    return sum(w in known for w in clean_words) / len(clean_words) >= 0.6
