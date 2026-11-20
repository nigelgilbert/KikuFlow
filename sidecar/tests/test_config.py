from pathlib import Path

import pytest

from kiku_sidecar.config import Config, load_config


def test_missing_file_gives_defaults(tmp_path: Path):
    config = load_config(tmp_path / "config.toml")
    assert config == Config(
        stt_engine="parakeet",
        stt_model="mlx-community/parakeet-tdt-0.6b-v3",
        cleanup_model="devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit",
        cleanup_prompt_file="",
        cleanup_prompt_role="",
    )


def test_partial_file_overrides_only_named_keys(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[stt]\nengine = "whisper"\n\n[cleanup]\nprompt_role = "user"\n')
    assert load_config(path) == Config(
        stt_engine="whisper",
        stt_model="mlx-community/whisper-large-v3-turbo",
        cleanup_prompt_role="user",
    )


def test_explicit_stt_model_wins_over_engine_default(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[stt]\nengine = "whisper"\nmodel = "mlx-community/whisper-tiny"\n')
    assert load_config(path).stt_model == "mlx-community/whisper-tiny"


def test_wrongly_typed_value_is_rejected(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text("[stt]\nengine = 1\n")
    with pytest.raises(TypeError, match="stt_engine must be str"):
        load_config(path)


def test_leftover_safety_check_is_ignored(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text("[cleanup]\nsafety_check = false\n")
    assert load_config(path) == Config()


def test_cleanup_prompt_keys_are_read(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[cleanup]\nprompt_file = "p.txt"\nprompt_role = "user"\n')
    config = load_config(path)
    assert (config.cleanup_prompt_file, config.cleanup_prompt_role) == ("p.txt", "user")


@pytest.mark.parametrize(
    ("line", "error"),
    [
        ("prompt_file = 1", "cleanup_prompt_file must be str"),
        ("prompt_role = true", "cleanup_prompt_role must be str"),
    ],
)
def test_wrongly_typed_cleanup_prompt_keys_are_rejected(tmp_path: Path, line: str, error: str):
    path = tmp_path / "config.toml"
    path.write_text(f"[cleanup]\n{line}\n")
    with pytest.raises(TypeError, match=error):
        load_config(path)
