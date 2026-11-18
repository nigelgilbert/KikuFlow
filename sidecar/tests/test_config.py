from pathlib import Path

from slopr_sidecar.config import Config, load_config


def test_missing_file_gives_defaults(tmp_path: Path):
    config = load_config(tmp_path / "config.toml")
    assert config == Config(
        stt_engine="parakeet",
        stt_model="mlx-community/parakeet-tdt-0.6b-v3",
        cleanup_enabled=True,
        cleanup_model="ReFyneLabs/simplewords-dictation-cleanup-v3",
        port=48123,
    )


def test_partial_file_overrides_only_named_keys(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text('[stt]\nengine = "whisper"\n\n[cleanup]\nenabled = false\n')
    assert load_config(path) == Config(stt_engine="whisper", cleanup_enabled=False)
