import asyncio
import threading
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from slopr_sidecar import lifecycle, server
from slopr_sidecar.config import Config

SPEECH = np.zeros(16_000, "<f4").tobytes()  # one second of raw float32 PCM
RAW = "um so we should uh meet on Friday"

# A hook file that appends each call, and whether log.txt exists yet, to calls.txt next to it,
# after the other hook files.
RECORDER = """
import asyncio
import threading
from pathlib import Path

def record(point, t):
    logged = Path(__file__).parents[1].joinpath("log.txt").exists()
    with Path(__file__).with_name("calls.txt").open("a") as f:
        print(point, t, threading.current_thread().name, logged, sep="|", file=f)

def on_transcribed(t): record("on_transcribed", t)
def on_cleaned(t): record("on_cleaned", t)
def on_output(t): record("on_output", t)
def on_done(t): record("on_done", t)
"""


class Fakes:
    def __init__(self) -> None:
        self.config = Config()
        self.cleaned = "We should meet on Friday."
        self.cleaner_inputs: list[str] = []
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

        def clean(raw: str) -> str:
            self.cleaner_inputs.append(raw)
            return self.cleaned

        return clean


@pytest.fixture
def hooks(tmp_path: Path) -> Path:
    """The user hook directory, holding the recorder."""
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks/zz_recorder.py").write_text(RECORDER)
    return tmp_path / "hooks"


def calls(hooks: Path) -> list[list[str]]:
    path = hooks / "calls.txt"
    return [line.split("|") for line in path.read_text().splitlines()] if path.exists() else []


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, hooks: Path) -> Fakes:
    """Fake models, and temporary stand-ins for the hook directory and the log."""
    fakes = Fakes()
    monkeypatch.setattr(server, "HOOK_DIR", hooks)
    monkeypatch.setattr(lifecycle, "LOG", tmp_path / "log.txt")
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


def test_hooks_shape_the_text_around_cleanup(
    fakes: Fakes, hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "a.py").write_text(
        "def on_transcribed(t): return 'please call Anna tomorrow'\n"
        "def on_cleaned(t): return t + '!'\n"
    )
    fakes.cleaned = "Please call Anna tomorrow."
    client.post("/reload")
    body = client.post("/transcribe", content=SPEECH).json()
    # The cleaner and its plausibility check see the hook's text, not the raw transcript.
    assert fakes.cleaner_inputs[-1] == "please call Anna tomorrow"
    assert body["raw"] == RAW
    assert body["clean"] == "Please call Anna tomorrow.!"
    assert set(body["timings"]) == {"stt_ms", "cleanup_ms"}
    assert [c[:2] for c in calls(hooks)] == [
        ["on_transcribed", "please call Anna tomorrow"],
        ["on_cleaned", "Please call Anna tomorrow.!"],
        ["on_output", "Please call Anna tomorrow.!"],
        ["on_done", "Please call Anna tomorrow.!"],
    ]
    # The recorder's on_output returns None, so the text that was output is logged.
    assert (tmp_path / "log.txt").read_text() == "Please call Anna tomorrow.!"


@pytest.mark.parametrize(("query", "enabled"), [("?cleanup=false", True), ("", False)])
def test_on_cleaned_fires_with_cleanup_off(fakes: Fakes, hooks: Path, query: str, enabled: bool):
    fakes.config = Config(cleanup_enabled=enabled)
    with TestClient(server.app) as client:
        assert client.post("/transcribe" + query, content=SPEECH).json()["clean"] == RAW
    assert ["on_cleaned", RAW] in [c[:2] for c in calls(hooks)]


def test_empty_transcription_fires_no_hooks(hooks: Path, client: TestClient):
    assert client.post("/transcribe", content=b"").json()["clean"] == ""
    assert calls(hooks) == []


def test_hook_returning_empty_text_stops_the_pipeline(
    fakes: Fakes, hooks: Path, client: TestClient
):
    (hooks / "a.py").write_text("def on_transcribed(t): return ''\n")
    client.post("/reload")
    assert client.post("/transcribe", content=SPEECH).json()["clean"] == ""
    assert set(fakes.cleaner_inputs) == {"Hello there."}  # only the warm-up passes
    assert calls(hooks) == []


def test_run_leaves_on_done_for_after_the_reply(hooks: Path, client: TestClient):
    wait_for_load()
    audio = np.zeros(16_000, "<f4")
    _, after = server.executor.submit(server.run, audio, True).result()
    assert [c[0] for c in calls(hooks)] == ["on_transcribed", "on_cleaned"]
    after()
    assert [c[0] for c in calls(hooks)] == ["on_transcribed", "on_cleaned", "on_output", "on_done"]


def test_hooks_after_the_reply_fire_once_on_the_model_executor(hooks: Path, client: TestClient):
    client.post("/transcribe", content=SPEECH)
    after = [c for c in calls(hooks) if c[0] in ("on_output", "on_done")]
    executor = server.executor.submit(lambda: threading.current_thread().name).result()
    assert [(c[0], c[2]) for c in after] == [("on_output", executor), ("on_done", executor)]


def test_hook_file_failing_to_load_leaves_health_alone(hooks: Path, client: TestClient):
    (hooks / "broken.py").write_text("raise RuntimeError('broken hook file')\n")
    client.post("/reload")
    wait_for_load()
    health = client.get("/health").json()
    assert (health["ready"], health["error"]) == (True, None)


def test_reply_is_sent_before_on_output(hooks: Path, client: TestClient):
    wait_for_load()
    at_reply = []

    async def receive():
        return {"type": "http.request", "body": SPEECH}

    async def send(message):
        if message["type"] == "http.response.body":
            at_reply.append([c[0] for c in calls(hooks)])

    path = {"type": "http", "method": "POST", "path": "/transcribe", "query_string": b""}
    asyncio.run(server.app({**path, "headers": []}, receive, send))
    assert at_reply == [["on_transcribed", "on_cleaned"]]
    assert calls(hooks)[-1][0] == "on_done"


def test_log_is_written_without_hook_files(hooks: Path, tmp_path: Path, client: TestClient):
    (hooks / "zz_recorder.py").unlink()
    client.post("/reload")
    client.post("/transcribe", content=SPEECH)
    assert (tmp_path / "log.txt").read_text() == "We should meet on Friday."


def test_log_py_is_just_another_hook_file(hooks: Path, tmp_path: Path, client: TestClient):
    (hooks / "log.py").write_text("")
    client.post("/reload")
    client.post("/transcribe", content=SPEECH)
    assert (tmp_path / "log.txt").read_text() == "We should meet on Friday."
    assert calls(hooks)[-1][0] == "on_done"


def test_on_output_fires_before_the_log_is_written_and_on_done_after(
    hooks: Path, client: TestClient
):
    client.post("/transcribe", content=SPEECH)
    assert [[c[0], c[3]] for c in calls(hooks)][-2:] == [
        ["on_output", "False"],
        ["on_done", "True"],
    ]


def test_failed_log_write_is_logged_and_on_done_still_fires(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    hooks: Path,
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
):
    monkeypatch.setattr(lifecycle, "LOG", tmp_path / "missing/log.txt")
    client.post("/transcribe", content=SPEECH)
    assert "log write failed" in caplog.text
    assert calls(hooks)[-1][0] == "on_done"


def test_on_output_decides_what_is_logged_but_not_the_reply(
    hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "a.py").write_text("def on_output(t): return t.upper()\n")
    client.post("/reload")
    assert client.post("/transcribe", content=SPEECH).json()["clean"] == "We should meet on Friday."
    assert (tmp_path / "log.txt").read_text() == "WE SHOULD MEET ON FRIDAY."
    assert calls(hooks)[-1][:2] == ["on_done", "WE SHOULD MEET ON FRIDAY."]


def test_on_output_returning_empty_text_skips_the_log_and_on_done(
    hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "a.py").write_text("def on_output(t): return ''\n")
    client.post("/reload")
    assert client.post("/transcribe", content=SPEECH).json()["clean"] == "We should meet on Friday."
    assert not (tmp_path / "log.txt").exists()
    assert [c[0] for c in calls(hooks)] == ["on_transcribed", "on_cleaned"]
