"""The chat models that plugins bring: one copy of each, shared by every plugin that names it."""

from functools import cache
from typing import Literal

from mlx_lm import generate, load

type Engine = Literal["mlx"]
type Examples = tuple[tuple[str, str], ...]
type Messages = list[dict[str, str]]


def chat_messages(system: str, text: str, examples: Examples) -> Messages:
    """Return the chat for `text`: the system prompt, each example, then `text`."""
    messages = [{"role": "system", "content": system}]
    for said, reply in examples:
        messages.append({"role": "user", "content": said})
        messages.append({"role": "assistant", "content": reply})
    messages.append({"role": "user", "content": text})
    return messages


class Model:
    """A chat model that a plugin prompts. Each engine has its own subclass."""

    def prompt(self, system: str, text: str, examples: Examples = ()) -> str:
        """Return the model's reply to `text` under the system prompt.

        Each example is a pair, what a user said and the reply to give, shown to the model first.
        """
        raise NotImplementedError


class MLXModel(Model):
    """A chat model that mlx-lm runs, from a Hugging Face repo or a local folder."""

    def __init__(self, name: str) -> None:
        self.model, self.tokenizer = load(name)[:2]

    def prompt(self, system: str, text: str, examples: Examples = ()) -> str:
        messages = chat_messages(system, text, examples)
        chat = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        # Room for a reply that expands the text, but a runaway generation still stops.
        max_tokens = 4 * len(self.tokenizer.encode(text)) + 64
        reply = generate(self.model, self.tokenizer, chat, max_tokens=max_tokens)
        return reply.strip()


@cache
def load_once(engine: Engine, name: str) -> Model:
    """Return the model `name` on `engine`, the same one for every call.

    A load that fails is not kept, so the next call tries again.
    """
    match engine:
        case "mlx":
            return MLXModel(name)
        case _:
            raise ValueError(f"unknown engine {engine!r}; expected 'mlx'")


def load_model(name: str, engine: Engine = "mlx") -> Model:
    """Return the chat model `name`, loaded once however many plugins ask for it.

    `name` is whatever the engine loads. For "mlx" that is a Hugging Face repo or a local folder.
    """
    return load_once(engine, name)
