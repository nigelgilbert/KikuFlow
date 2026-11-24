import pytest

from kiku import load_model
from kiku_sidecar import chat_model
from kiku_sidecar.chat_model import Messages, MLXModel, load_once


class FakeTokenizer:
    def apply_chat_template(
        self, messages: Messages, add_generation_prompt: bool, tokenize: bool
    ) -> Messages:
        return messages

    def encode(self, text: str) -> list[str]:
        return text.split()


@pytest.fixture
def loads(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Return the names mlx-lm was asked to load, with the load faked and the cache empty."""
    names: list[str] = []

    def load(name: str) -> tuple[str, FakeTokenizer]:
        names.append(name)
        return f"weights of {name}", FakeTokenizer()

    monkeypatch.setattr(chat_model, "load", load)
    load_once.cache_clear()
    return names


def test_plugins_that_name_one_model_share_it(loads: list[str]):
    first = load_model("some/model")
    second = load_model("some/model", engine="mlx")
    assert first is second
    assert loads == ["some/model"]


def test_another_name_is_another_model(loads: list[str]):
    assert load_model("some/model") is not load_model("other/model")
    assert loads == ["some/model", "other/model"]


def test_unknown_engine_fails(loads: list[str]):
    with pytest.raises(ValueError, match="unknown engine 'llama_cpp'"):
        load_model("some/model", engine="llama_cpp")  # pyright: ignore[reportArgumentType]
    assert loads == []


def test_failed_load_is_tried_again(monkeypatch: pytest.MonkeyPatch, loads: list[str]):
    def missing(name: str) -> None:
        raise FileNotFoundError(name)

    with monkeypatch.context() as patch:
        patch.setattr(chat_model, "load", missing)
        with pytest.raises(FileNotFoundError):
            load_model("some/model")
    assert isinstance(load_model("some/model"), MLXModel)


def test_prompt_shows_the_examples_then_the_text(monkeypatch: pytest.MonkeyPatch, loads: list[str]):
    calls = []

    def generate(model: str, tokenizer: FakeTokenizer, chat: Messages, max_tokens: int) -> str:
        calls.append((model, chat, max_tokens))
        return " a reply\n"

    monkeypatch.setattr(chat_model, "generate", generate)
    model = load_model("some/model")
    reply = model.prompt("Be brief.", "three words here", (("hi", "hello"),))
    assert reply == "a reply"
    chat = [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "three words here"},
    ]
    assert calls == [("weights of some/model", chat, 4 * 3 + 64)]
