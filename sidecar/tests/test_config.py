from pathlib import Path

import pytest

from slopr_sidecar.config import Config, load_config


def test_missing_file_gives_defaults(tmp_path: Path):
    config = load_config(tmp_path / "config.toml")
    assert config == Config(
        stt_engine="parakeet",
        stt_model="mlx-community/parakeet-tdt-0.6b-v3",
        cleanup_model="ReFyneLabs/simplewords-dictation-cleanup-v3",
        cleanup_prompt_file="",
        cleanup_prompt_role="",
        cleanup_safety_check=True,
        port=48123,
    )


def test_partial_file_overrides_only_named_keys(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[stt]\nengine = "whisper"\n\n[cleanup]\nsafety_check = false\n')
    assert load_config(path) == Config(
        stt_engine="whisper",
        stt_model="mlx-community/whisper-large-v3-turbo",
        cleanup_safety_check=False,
    )


def test_explicit_stt_model_wins_over_engine_default(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[stt]\nengine = "whisper"\nmodel = "mlx-community/whisper-tiny"\n')
    assert load_config(path).stt_model == "mlx-community/whisper-tiny"


def test_wrongly_typed_value_is_rejected(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[cleanup]\nsafety_check = "false"\n')
    with pytest.raises(TypeError, match="cleanup_safety_check must be bool"):
        load_config(path)


def test_cleanup_prompt_keys_are_read(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[cleanup]\nprompt_file = "p.txt"\nprompt_role = "user"\nsafety_check = false\n'
    )
    config = load_config(path)
    assert (config.cleanup_prompt_file, config.cleanup_prompt_role) == ("p.txt", "user")
    assert config.cleanup_safety_check is False


@pytest.mark.parametrize(
    ("line", "error"),
    [
        ("prompt_file = 1", "cleanup_prompt_file must be str"),
        ("prompt_role = true", "cleanup_prompt_role must be str"),
        ('safety_check = "false"', "cleanup_safety_check must be bool"),
    ],
)
def test_wrongly_typed_cleanup_prompt_keys_are_rejected(tmp_path: Path, line: str, error: str):
    path = tmp_path / "config.toml"
    path.write_text(f"[cleanup]\n{line}\n")
    with pytest.raises(TypeError, match=error):
        load_config(path)
