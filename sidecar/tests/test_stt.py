import io
import wave

import numpy as np
import pytest

from kiku_sidecar import stt
from kiku_sidecar.stt import decode_audio, load_transcriber


def test_wav_and_raw_pcm_decode_to_the_same_samples():
    pcm = np.array([0, 16384, -16384, 32767, -32768], dtype="<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16_000)
        w.writeframes(pcm.tobytes())
    expected = pcm.astype(np.float32) / 32768

    from_wav = decode_audio(buf.getvalue())
    from_raw = decode_audio(expected.astype("<f4").tobytes())

    assert from_wav.dtype == from_raw.dtype == np.float32
    np.testing.assert_array_equal(from_wav, expected)
    np.testing.assert_array_equal(from_raw, expected)


def test_wav_with_wrong_rate_is_rejected():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44_100)
        w.writeframes(b"\0\0")
    with pytest.raises(ValueError, match="16 kHz"):
        decode_audio(buf.getvalue())


def test_unknown_engine_fails_at_load():
    with pytest.raises(ValueError, match="unknown stt.engine 'vosk'"):
        load_transcriber("vosk", "some/model", [])


@pytest.mark.parametrize(
    ("terms", "hint"),
    [(["Claude", "Mac"], "Claude, Mac"), ([], None)],
)
def test_whisper_gets_the_terms_as_its_initial_prompt(
    monkeypatch: pytest.MonkeyPatch, terms: list[str], hint: str | None
):
    calls: list[dict[str, object]] = []

    def transcribe(audio: np.ndarray, **options: object) -> dict[str, str]:
        calls.append(options)
        return {"text": " Hello there. "}

    monkeypatch.setattr(stt.mlx_whisper, "transcribe", transcribe)
    transcriber = load_transcriber("whisper", "some/whisper", terms)
    assert transcriber(np.zeros(16_000, np.float32)) == "Hello there."
    assert calls == [{"path_or_hf_repo": "some/whisper", "initial_prompt": hint}]
