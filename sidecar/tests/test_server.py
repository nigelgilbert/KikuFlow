import threading
from collections.abc import Iterator

import numpy as np
import pytest
from fastapi.testclient import TestClient

from slopr_sidecar import server
from slopr_sidecar.config import Config

SPEECH = np.zeros(16_000, "<f4").tobytes()  # one second of raw float32 PCM
RAW = "um so we should uh meet on Friday"


class Fakes:
    def __init__(self) -> None:
        self.config = Config()
        self.cleaned = "We should meet on Friday."
        self.cleaner_loads = 0
        self.loaded = threading.Event()
        self.loaded.set()

    def load_transcriber(self, engine: str, model: str):
        self.loaded.wait()
        if engine == "vosk":
            raise ValueError("unknown stt.engine 'vosk'")
        return lambda audio: RAW

    def load_cleaner(self, model: str):
        self.cleaner_loads += 1
        return lambda raw: self.cleaned


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> Fakes:
    fakes = Fakes()
    monkeypatch.setattr(server, "load_config", lambda: fakes.config)
    monkeypatch.setattr(server, "load_transcriber", fakes.load_transcriber)
    monkeypatch.setattr(server, "load_cleaner", fakes.load_cleaner)
    return fakes


@pytest.fixture
def client(fakes: Fakes) -> Iterator[TestClient]:
    with TestClient(server.app) as client:
        yield client


def wait_for_load() -> None:
    server.executor.submit(lambda: None).result()


def test_health_answers_while_loading_then_reports_models(fakes: Fakes, client: TestClient):
    fakes.loaded.clear()
    client.post("/reload")
    assert client.get("/health").json()["ready"] is False
    fakes.loaded.set()
    wait_for_load()
    assert client.get("/health").json() == {
        "ready": True,
        "error": None,
        "stt_engine": "parakeet",
        "stt_model": "mlx-community/parakeet-tdt-0.6b-v3",
        "cleanup_model": "ReFyneLabs/simplewords-dictation-cleanup-v3",
    }


def test_transcribe_with_cleanup(client: TestClient):
    body = client.post("/transcribe", content=SPEECH).json()
    assert body["raw"] == RAW
    assert body["clean"] == "We should meet on Friday."
    assert set(body["timings"]) == {"stt_ms", "cleanup_ms"}


def test_transcribe_with_cleanup_off_by_query(client: TestClient):
    body = client.post("/transcribe?cleanup=false", content=SPEECH).json()
    assert body["clean"] == body["raw"] == RAW


def test_cleanup_off_by_config_does_not_load_the_model(fakes: Fakes):
    fakes.config = Config(cleanup_enabled=False)
    with TestClient(server.app) as client:
        body = client.post("/transcribe", content=SPEECH).json()
        assert body["clean"] == body["raw"] == RAW
        assert client.get("/health").json()["cleanup_model"] is None
    assert fakes.cleaner_loads == 0


def test_implausible_cleanup_falls_back_to_raw(fakes: Fakes, client: TestClient):
    fakes.cleaned = "Friday is the fifth day of the week, named after the goddess Frigg."
    assert client.post("/transcribe", content=SPEECH).json()["clean"] == RAW


def test_bad_audio_is_rejected(client: TestClient):
    assert client.post("/transcribe", content=b"RIFF").status_code == 400


def test_reload_rereads_config(fakes: Fakes, client: TestClient):
    wait_for_load()
    fakes.config = Config(stt_engine="whisper", stt_model="mlx-community/whisper-tiny")
    assert client.post("/reload").json()["ready"] is False
    wait_for_load()
    health = client.get("/health").json()
    assert (health["stt_engine"], health["stt_model"]) == ("whisper", "mlx-community/whisper-tiny")
    assert fakes.cleaner_loads == 2


def test_load_failure_is_reported(fakes: Fakes):
    fakes.config = Config(stt_engine="vosk")
    with TestClient(server.app) as client:
        wait_for_load()
        health = client.get("/health").json()
        assert health["ready"] is False
        assert health["error"] == "ValueError: unknown stt.engine 'vosk'"
        assert client.post("/transcribe", content=SPEECH).status_code == 503
