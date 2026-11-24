"""Speech-to-text: decode request audio and run the configured engine."""

import io
import wave
from collections.abc import Callable

import mlx.core as mx
import mlx_whisper
import numpy as np
from parakeet_mlx import from_pretrained
from parakeet_mlx.audio import get_logmel

SAMPLE_RATE = 16_000

type Transcriber = Callable[[np.ndarray], str]


def decode_audio(body: bytes) -> np.ndarray:
    """Decode 16 kHz mono audio: 16-bit PCM WAV (RIFF header) or raw float32 little-endian."""
    if body[:4] != b"RIFF":
        return np.frombuffer(body, "<f4")
    with wave.open(io.BytesIO(body)) as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError("WAV must be 16 kHz, mono, 16-bit PCM")
        pcm = np.frombuffer(w.readframes(w.getnframes()), "<i2")
    return pcm.astype(np.float32) / 32768


def load_transcriber(engine: str, model: str, terms: list[str]) -> Transcriber:
    """Return the transcriber for `engine` and `model`.

    Whisper gets `terms` as a hint to the model, and Parakeet has no way to take one.
    """
    match engine:
        case "parakeet":
            parakeet = from_pretrained(model)

            def transcribe(audio: np.ndarray) -> str:
                mel = get_logmel(mx.array(audio), parakeet.preprocessor_config)
                return parakeet.generate(mel)[0].text.strip()

            return transcribe
        case "whisper":
            # None, Whisper's default, when there are no terms.
            hint = ", ".join(terms) or None

            def transcribe_with_whisper(audio: np.ndarray) -> str:
                result = mlx_whisper.transcribe(audio, path_or_hf_repo=model, initial_prompt=hint)
                return str(result["text"]).strip()

            return transcribe_with_whisper
        case _:
            raise ValueError(f"unknown stt.engine {engine!r}; expected 'parakeet' or 'whisper'")
