import json
import tomllib
from pathlib import Path

import pytest

from slopr_sidecar.config import Config, load_config, main


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
        hotkey_key="right_option",
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


def test_hotkey_key_is_read(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[hotkey]\nkey = "fn"\n')
    assert load_config(path).hotkey_key == "fn"


def test_wrongly_typed_hotkey_key_is_rejected(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text("[hotkey]\nkey = 3\n")
    with pytest.raises(TypeError, match="hotkey_key must be str"):
        load_config(path)


def test_main_prints_the_config_as_one_line_of_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    path = tmp_path / "config.toml"
    path.write_text('[server]\nport = 9000\n\n[hotkey]\nkey = "fn"\n')
    monkeypatch.setattr(load_config, "__defaults__", (path,))
    main()
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    config = json.loads(lines[0])
    assert (config["port"], config["hotkey_key"]) == (9000, "fn")


def test_main_raises_on_invalid_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "config.toml"
    path.write_text("[server\nport = 9000\n")
    monkeypatch.setattr(load_config, "__defaults__", (path,))
    with pytest.raises(tomllib.TOMLDecodeError):
        main()
