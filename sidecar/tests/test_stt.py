import io
import wave

import numpy as np
import pytest

from slopr_sidecar.stt import decode_audio, load_transcriber


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
        load_transcriber("vosk", "some/model")
