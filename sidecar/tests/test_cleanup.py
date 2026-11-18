from pathlib import Path

import pytest

from slopr_sidecar import cleanup
from slopr_sidecar.cleanup import REFYNE, UTTER, build_messages, is_plausible, load_cleaner

RAW = "um so I think we should uh meet on Thursday no wait Friday at noon works better"


def test_real_cleanup_passes():
    assert is_plausible(RAW, "I think we should meet on Friday at noon. That works better.")


def test_self_correction_that_drops_most_words_passes():
    raw = "Let's meet Thursday. No, no, wait, uh we'll meet Friday actually."
    assert is_plausible(raw, "Let's meet Friday.")


def test_length_blow_up_fails():
    assert not is_plausible("meet on Friday", "meet on Friday " * 4)


def test_answering_a_dictated_question_fails():
    raw = "how do I reverse a list in python"
    answer = "You can call the reverse method, or use slicing with a step of minus one."
    assert not is_plausible(raw, answer)


def test_empty_output_fails():
    assert not is_plausible(RAW, "")


def test_unsupported_model_fails_at_load():
    with pytest.raises(ValueError, match="set cleanup.prompt_file"):
        load_cleaner("some/other-model")


@pytest.fixture
def app_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(cleanup, "APP_DIR", tmp_path)
    return tmp_path


def test_utter_prompt_is_the_system_turn_with_its_final_newline():
    system = Path(cleanup.__file__).with_name("utter_system.txt").read_text(encoding="utf-8")
    assert system.endswith("\n")
    assert build_messages(UTTER, "", "")("hi") == [
        {"role": "system", "content": system},
        {"role": "user", "content": "hi"},
    ]


def test_refyne_prompt_is_stripped_into_the_user_turn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    (tmp_path / "system_v2.txt").write_text("\nClean this up.\n")
    downloads = []

    def download(repo: str, name: str) -> str:
        downloads.append((repo, name))
        return str(tmp_path / name)

    monkeypatch.setattr(cleanup, "hf_hub_download", download)
    messages = build_messages(REFYNE, "", "")("hi")
    assert messages == [{"role": "user", "content": "Clean this up.\n\nhi"}]
    assert downloads == [(REFYNE, "system_v2.txt")]


def test_built_in_placement_can_be_overridden():
    messages = build_messages(UTTER, "", "user")("hi")
    assert [m["role"] for m in messages] == ["user"]
    assert messages[0]["content"].endswith("\n\nhi")


@pytest.mark.parametrize("model", [REFYNE, UTTER, "some/other-model"])
def test_prompt_file_replaces_the_built_in_prompt(
    monkeypatch: pytest.MonkeyPatch, app_dir: Path, model: str
):
    monkeypatch.setattr(cleanup, "hf_hub_download", None)  # never called
    (app_dir / "prompt.txt").write_text("Translate to French.\n")
    assert build_messages(model, "prompt.txt", "system")("hi") == [
        {"role": "system", "content": "Translate to French.\n"},
        {"role": "user", "content": "hi"},
    ]
    assert build_messages(model, "prompt.txt", "user")("hi") == [
        {"role": "user", "content": "Translate to French.\n\nhi"},
    ]


def test_unknown_model_defaults_to_system_placement(app_dir: Path):
    (app_dir / "prompt.txt").write_text("Translate to French.")
    assert [m["role"] for m in build_messages("some/other-model", "prompt.txt", "")("hi")] == [
        "system",
        "user",
    ]


def test_prompt_file_is_used_with_the_built_in_placement(app_dir: Path):
    (app_dir / "prompt.txt").write_text("Fix it.\n")
    assert build_messages(REFYNE, "prompt.txt", "")("hi") == [
        {"role": "user", "content": "Fix it.\n\nhi"}
    ]


def test_bad_placement_fails_at_load():
    with pytest.raises(ValueError, match='cleanup.placement must be "system" or "user"'):
        build_messages(UTTER, "", "assistant")


def test_missing_prompt_file_fails_naming_the_path(app_dir: Path):
    with pytest.raises(FileNotFoundError, match=f"{app_dir / 'nope.txt'} not found"):
        build_messages(UTTER, "nope.txt", "")


def test_empty_prompt_file_fails_naming_the_path(app_dir: Path):
    (app_dir / "blank.txt").write_text(" \n\t\n")
    with pytest.raises(ValueError, match=f"{app_dir / 'blank.txt'} is empty"):
        build_messages(UTTER, "blank.txt", "")


def test_prompt_path_resolution(monkeypatch: pytest.MonkeyPatch, app_dir: Path):
    monkeypatch.setenv("HOME", "/Users/someone")
    assert cleanup.prompt_path("~/p.txt") == Path("/Users/someone/p.txt")
    assert cleanup.prompt_path("prompts/p.txt") == app_dir / "prompts/p.txt"
    assert cleanup.prompt_path("/etc/p.txt") == Path("/etc/p.txt")
