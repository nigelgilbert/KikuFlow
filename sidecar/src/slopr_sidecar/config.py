"""Config from ~/Library/Application Support/SloprFlow/config.toml."""

import json
import sys
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path

APP_DIR = Path.home() / "Library/Application Support/SloprFlow"

# Default stt.model for each stt.engine, so changing only the engine works.
STT_MODELS = {
    "parakeet": "mlx-community/parakeet-tdt-0.6b-v3",
    "whisper": "mlx-community/whisper-large-v3-turbo",
}


@dataclass(frozen=True)
class Config:
    stt_engine: str = "parakeet"
    stt_model: str = STT_MODELS["parakeet"]
    cleanup_model: str = "ReFyneLabs/simplewords-dictation-cleanup-v3"
    cleanup_prompt_file: str = ""
    cleanup_prompt_role: str = ""
    cleanup_safety_check: bool = True
    port: int = 48123
    hotkey_key: str = "right_option"


def load_config(path: Path = APP_DIR / "config.toml") -> Config:
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    stt, cleanup, server, hotkey = (data.get(k, {}) for k in ("stt", "cleanup", "server", "hotkey"))
    d = Config()
    engine = stt.get("engine", d.stt_engine)
    config = Config(
        stt_engine=engine,
        stt_model=stt.get("model", STT_MODELS.get(engine, d.stt_model)),
        cleanup_model=cleanup.get("model", d.cleanup_model),
        cleanup_prompt_file=cleanup.get("prompt_file", d.cleanup_prompt_file),
        cleanup_prompt_role=cleanup.get("prompt_role", d.cleanup_prompt_role),
        cleanup_safety_check=cleanup.get("safety_check", d.cleanup_safety_check),
        port=server.get("port", d.port),
        hotkey_key=hotkey.get("key", d.hotkey_key),
    )
    for f in fields(config):
        value, default = getattr(config, f.name), getattr(d, f.name)
        if type(value) is not type(default):
            raise TypeError(f"config {f.name} must be {type(default).__name__}, got {value!r}")
    return config


def main() -> None:
    """Print the config as one line of JSON, for the app; a bad config exits with one line."""
    try:
        print(json.dumps(asdict(load_config())))
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"config line {e.lineno}: {e.msg}")
    except TypeError as e:
        sys.exit(str(e))
