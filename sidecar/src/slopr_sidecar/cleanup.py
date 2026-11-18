"""LLM cleanup of the raw transcript, and a safety check against the model going off-script."""

import re
from collections.abc import Callable
from pathlib import Path

from huggingface_hub import hf_hub_download
from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

from .config import APP_DIR

type Cleaner = Callable[[str], str]
type Messages = list[dict[str, str]]


REFYNE = "ReFyneLabs/simplewords-dictation-cleanup-v3"
UTTER = "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"


def _refyne_prompt() -> str:
    # Frozen prompt shipped in the model repo.
    return Path(hf_hub_download(REFYNE, "system_v2.txt")).read_text(encoding="utf-8")


def _utter_prompt() -> str:
    # The MLX repo doesn't ship it; utter_system.txt is the "System prompt" block of the model
    # card at hpal007/utter-dictation-cleanup-GGUF@68bbbf5589c85cbb18818c3a0609cfc90eb63dd5.
    return Path(__file__).with_name("utter_system.txt").read_text(encoding="utf-8")


# Each built-in model was trained on one exact prompt: how to get it, and where it goes.
PRESETS: dict[str, tuple[Callable[[], str], str]] = {
    REFYNE: (_refyne_prompt, "user"),
    UTTER: (_utter_prompt, "system"),
}


def prompt_path(prompt_file: str) -> Path:
    """`~` expanded; a relative path is under APP_DIR."""
    return APP_DIR / Path(prompt_file).expanduser()


def _read_prompt_file(prompt_file: str) -> str:
    path = prompt_path(prompt_file)
    if not path.is_file():
        raise FileNotFoundError(f"cleanup.prompt_file {path} not found")
    prompt = path.read_text(encoding="utf-8")
    if not prompt.strip():
        raise ValueError(f"cleanup.prompt_file {path} is empty")
    return prompt


def build_messages(model: str, prompt_file: str, placement: str) -> Callable[[str], Messages]:
    """The chat for each transcript: `prompt_file` or the model's built-in prompt, placed."""
    preset = PRESETS.get(model)
    placement = placement or (preset[1] if preset else "system")
    if placement not in ("system", "user"):
        raise ValueError(f'cleanup.placement must be "system" or "user", got {placement!r}')
    if prompt_file:
        prompt = _read_prompt_file(prompt_file)
    elif preset:
        prompt = preset[0]()
    else:
        raise ValueError(f"unsupported cleanup.model {model!r}: set cleanup.prompt_file to use it")
    if placement == "user":
        # One user turn, no system role.
        prompt = prompt.strip()
        return lambda raw: [{"role": "user", "content": f"{prompt}\n\n{raw}"}]
    # Verbatim, final newline included.
    return lambda raw: [{"role": "system", "content": prompt}, {"role": "user", "content": raw}]


def load_cleaner(model_name: str, prompt_file: str = "", placement: str = "") -> Cleaner:
    messages = build_messages(model_name, prompt_file, placement)
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
