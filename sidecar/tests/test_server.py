import asyncio
import re
import threading
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from kiku_sidecar import cleanup, lifecycle, server
from kiku_sidecar.config import Config, load_config

SPEECH = np.zeros(16_000, "<f4").tobytes()  # one second of raw float32 PCM
RAW = "um so we should uh meet on Friday"

# A hook file that appends each call, and whether log.txt exists yet, to calls.txt next to it,
# after the other hook files.
RECORDER = """
import threading
from pathlib import Path

def record(point, t):
    logged = Path(__file__).parents[1].joinpath("log.txt").exists()
    with Path(__file__).with_name("calls.txt").open("a") as f:
        print(point, t, threading.current_thread().name, logged, sep="|", file=f)

def on_transcribed(t):
    record("on_transcribed", t)
    return t

def on_cleaned(t):
    record("on_cleaned", t)
    return t

def on_sent(t):
    record("on_sent", t)
    return t

def on_done(t):
    record("on_done", t)
    return t
"""


class Fakes:
    def __init__(self) -> None:
        self.config = Config()
        self.cleaned = "We should meet on Friday."
        self.cleaner_inputs: list[str] = []
        self.transcriber_loads = 0
        self.cleaner_loads = 0
        self.failure: dict[str, Exception] = {}  # "stt" or "cleanup": what that model raises
        self.loaded = threading.Event()
        self.loaded.set()

    def load_transcriber(self, engine: str, model: str):
        self.loaded.wait()
        self.transcriber_loads += 1
        if engine == "vosk":
            raise ValueError("unknown stt.engine 'vosk'")

        def transcribe(audio) -> str:
            if "stt" in self.failure:
                raise self.failure["stt"]
            return RAW

        return transcribe

    def load_cleaner(self, config: Config):
        self.cleaner_loads += 1

        def clean(raw: str) -> str:
            self.cleaner_inputs.append(raw)
            if "cleanup" in self.failure:
                raise self.failure["cleanup"]
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


def errors(tmp_path: Path) -> list[str]:
    """The entries of errors.txt without their time."""
    path = tmp_path / "errors.txt"
    text = path.read_text() if path.exists() else ""
    return [entry[17:] for entry in filter(None, text.split("\n\n"))]


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, hooks: Path) -> Fakes:
    """Fake models, and temporary stand-ins for the hook directory, the log and errors.txt."""
    fakes = Fakes()
    monkeypatch.setattr(server, "HOOK_DIR", hooks)
    monkeypatch.setattr(lifecycle, "LOG_FILE", tmp_path / "log.txt")
    monkeypatch.setattr(lifecycle, "ERRORS", tmp_path / "errors.txt")
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


def test_health_answers_while_loading_then_reports_models(
    fakes: Fakes, tmp_path: Path, client: TestClient
):
    fakes.loaded.clear()
    server.start_loading()
    assert client.get("/health").json()["ready"] is False
    fakes.loaded.set()
    wait_for_load()
    assert client.get("/health").json() == {
        "ready": True,
        "error": None,
        "stt_engine": "parakeet",
        "stt_model": "mlx-community/parakeet-tdt-0.6b-v3",
        "cleanup_model": "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit",
    }
    assert errors(tmp_path) == []


def test_transcribe_with_cleanup(client: TestClient):
    body = client.post("/transcribe", content=SPEECH).json()
    assert body["raw"] == RAW
    assert body["clean"] == "We should meet on Friday."
    assert set(body["timings"]) == {"stt_ms", "cleanup_ms"}


def test_leftover_cleanup_enabled_is_ignored(fakes: Fakes, tmp_path: Path):
    (tmp_path / "config.toml").write_text("[cleanup]\nenabled = false\n")
    fakes.config = load_config(tmp_path / "config.toml")
    with TestClient(server.app) as client:
        assert client.post("/transcribe", content=SPEECH).json()["clean"] == fakes.cleaned


def test_cleanup_that_is_nothing_like_the_transcript_is_kept(fakes: Fakes, client: TestClient):
    fakes.cleaned = "Rendez-vous vendredi."
    assert client.post("/transcribe", content=SPEECH).json()["clean"] == "Rendez-vous vendredi."


def test_empty_cleanup_falls_back_to_raw(fakes: Fakes, client: TestClient):
    fakes.cleaned = ""
    assert client.post("/transcribe", content=SPEECH).json()["clean"] == RAW


def test_bad_audio_is_rejected_with_a_detail(client: TestClient):
    response = client.post("/transcribe", content=b"RIFF")  # EOFError with no message
    assert (response.status_code, response.json()) == (400, {"detail": "EOFError"})


def test_load_failure_is_reported(fakes: Fakes, tmp_path: Path):
    fakes.config = Config(stt_engine="vosk")
    with TestClient(server.app) as client:
        wait_for_load()
        health = client.get("/health").json()
        assert health["ready"] is False
        assert health["error"] == "ValueError: unknown stt.engine 'vosk'"
        assert client.post("/transcribe", content=SPEECH).status_code == 503
    [entry] = (tmp_path / "errors.txt").read_text().split("\n\n")
    assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d ValueError: unknown stt.engine 'vosk'", entry)


def test_missing_prompt_file_is_reported(
    monkeypatch: pytest.MonkeyPatch, fakes: Fakes, tmp_path: Path
):
    monkeypatch.setattr(server, "load_cleaner", cleanup.load_cleaner)  # fails before loading
    fakes.config = Config(cleanup_prompt_file=str(tmp_path / "nope.txt"))
    with TestClient(server.app) as client:
        wait_for_load()
        error = client.get("/health").json()["error"]
    assert error == f"FileNotFoundError: cleanup.prompt_file {tmp_path / 'nope.txt'} not found"


def test_hooks_shape_the_text_around_cleanup(
    fakes: Fakes, hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "a.py").write_text(
        "def on_transcribed(t): return 'please call Anna tomorrow'\n"
        "def on_cleaned(t): return t + '!'\n"
    )
    fakes.cleaned = "Please call Anna tomorrow."
    server.start_loading()
    body = client.post("/transcribe", content=SPEECH).json()
    # The cleaner and its plausibility check see the hook's text, not the raw transcript.
    assert fakes.cleaner_inputs[-1] == "please call Anna tomorrow"
    assert body["raw"] == RAW
    assert body["clean"] == "Please call Anna tomorrow.!"
    assert set(body["timings"]) == {"stt_ms", "cleanup_ms"}
    assert [c[:2] for c in calls(hooks)] == [
        ["on_transcribed", "please call Anna tomorrow"],
        ["on_cleaned", "Please call Anna tomorrow.!"],
        ["on_sent", "Please call Anna tomorrow.!"],
        ["on_done", "Please call Anna tomorrow.!"],
    ]
    assert (tmp_path / "log.txt").read_text() == "Please call Anna tomorrow.!"


def test_empty_transcription_fires_no_hooks(hooks: Path, client: TestClient):
    assert client.post("/transcribe", content=b"").json()["clean"] == ""
    assert calls(hooks) == []


def test_hook_returning_empty_text_stops_the_pipeline(
    fakes: Fakes, hooks: Path, client: TestClient
):
    (hooks / "a.py").write_text("def on_transcribed(t): return ''\n")
    server.start_loading()
    assert client.post("/transcribe", content=SPEECH).json()["clean"] == ""
    assert set(fakes.cleaner_inputs) == {"Hello there."}  # only the warm-up passes
    assert calls(hooks) == []


def test_run_leaves_on_sent_and_on_done_for_after_the_reply(hooks: Path, client: TestClient):
    wait_for_load()
    audio = np.zeros(16_000, "<f4")
    _, after = server.executor.submit(server.run, audio).result()
    assert [c[0] for c in calls(hooks)] == ["on_transcribed", "on_cleaned"]
    after()
    assert [c[0] for c in calls(hooks)] == ["on_transcribed", "on_cleaned", "on_sent", "on_done"]


def test_hooks_after_the_reply_fire_once_on_the_model_executor(hooks: Path, client: TestClient):
    client.post("/transcribe", content=SPEECH)
    after = [c for c in calls(hooks) if c[0] in ("on_sent", "on_done")]
    executor = server.executor.submit(lambda: threading.current_thread().name).result()
    assert [(c[0], c[2]) for c in after] == [("on_sent", executor), ("on_done", executor)]


def test_hook_file_failing_to_import_fails_the_load_before_the_models(
    fakes: Fakes, hooks: Path, tmp_path: Path
):
    (hooks / "broken.py").write_text("raise RuntimeError('broken hook file')\n")
    with TestClient(server.app) as client:
        wait_for_load()
        health = client.get("/health").json()
    assert health["ready"] is False
    assert health["error"] == "hook file broken.py: RuntimeError: broken hook file"
    assert (fakes.transcriber_loads, fakes.cleaner_loads) == (0, 0)
    assert errors(tmp_path) == [health["error"]]


def test_reply_is_sent_before_on_sent(hooks: Path, client: TestClient):
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
    server.start_loading()
    client.post("/transcribe", content=SPEECH)
    assert (tmp_path / "log.txt").read_text() == "We should meet on Friday."


def test_log_py_is_just_another_hook_file(hooks: Path, tmp_path: Path, client: TestClient):
    (hooks / "log.py").write_text("")
    server.start_loading()
    client.post("/transcribe", content=SPEECH)
    assert (tmp_path / "log.txt").read_text() == "We should meet on Friday."
    assert calls(hooks)[-1][0] == "on_done"


def test_on_sent_fires_before_the_log_is_written_and_on_done_after(hooks: Path, client: TestClient):
    client.post("/transcribe", content=SPEECH)
    assert [[c[0], c[3]] for c in calls(hooks)][-2:] == [
        ["on_sent", "False"],
        ["on_done", "True"],
    ]


def test_failed_log_write_is_recorded_and_stops_on_done(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, hooks: Path, client: TestClient
):
    monkeypatch.setattr(lifecycle, "LOG_FILE", tmp_path / "missing/log.txt")
    assert client.post("/transcribe", content=SPEECH).status_code == 200
    [entry] = errors(tmp_path)
    assert entry.startswith("log write: FileNotFoundError: ")
    assert calls(hooks)[-1][0] == "on_sent"


def test_on_sent_decides_what_is_logged_but_not_the_reply(
    hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "a.py").write_text("def on_sent(t): return t.upper()\n")
    server.start_loading()
    assert client.post("/transcribe", content=SPEECH).json()["clean"] == "We should meet on Friday."
    assert (tmp_path / "log.txt").read_text() == "WE SHOULD MEET ON FRIDAY."
    assert calls(hooks)[-1][:2] == ["on_done", "WE SHOULD MEET ON FRIDAY."]


@pytest.mark.parametrize("blank", ["", "  "])
def test_on_sent_returning_blank_text_skips_the_log_and_on_done(
    blank: str, hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "a.py").write_text(f"def on_sent(t): return {blank!r}\n")
    server.start_loading()
    assert client.post("/transcribe", content=SPEECH).json()["clean"] == "We should meet on Friday."
    assert not (tmp_path / "log.txt").exists()
    assert "on_done" not in [c[0] for c in calls(hooks)]


def test_hook_failing_before_the_reply_gives_500_with_its_message(
    fakes: Fakes, hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "voice.py").write_text("def on_cleaned(t):\n    return {}['x']\n")
    server.start_loading()
    response = client.post("/transcribe", content=SPEECH)
    assert response.status_code == 500
    assert response.json() == {"detail": "on_cleaned in voice.py:2: KeyError: 'x'"}
    assert [c[0] for c in calls(hooks)] == ["on_transcribed"]
    assert errors(tmp_path) == ["on_cleaned in voice.py:2: KeyError: 'x'"]


def test_hook_returning_a_wrong_type_before_the_reply_gives_500(
    hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "a.py").write_text("def on_cleaned(t): return {}\n")
    server.start_loading()
    response = client.post("/transcribe", content=SPEECH)
    detail = "on_cleaned in a.py: TypeError: on_cleaned returned dict, not str"
    assert (response.status_code, response.json()) == (500, {"detail": detail})
    assert [c[0] for c in calls(hooks)] == ["on_transcribed"]
    assert errors(tmp_path) == [detail]


@pytest.mark.parametrize(
    ("model", "failure", "detail"),
    [
        (
            "stt",
            RuntimeError("Metal\nout of memory"),
            "speech recognition: RuntimeError: Metal out of memory",
        ),
        ("cleanup", TimeoutError(), "cleanup model: TimeoutError"),
    ],
)
def test_model_failing_gives_500_with_its_label(
    fakes: Fakes,
    hooks: Path,
    tmp_path: Path,
    client: TestClient,
    model: str,
    failure: Exception,
    detail: str,
):
    wait_for_load()
    fakes.failure[model] = failure
    response = client.post("/transcribe", content=SPEECH)
    assert (response.status_code, response.json()) == (500, {"detail": detail})
    assert errors(tmp_path) == [detail]
    assert [c[0] for c in calls(hooks)] == (["on_transcribed"] if model == "cleanup" else [])


@pytest.mark.parametrize(
    ("point", "run"),
    [("on_sent", ["on_sent"]), ("on_done", ["on_sent", "on_done"])],
)
def test_hook_failing_after_the_reply_is_recorded_and_stops_the_rest(
    hooks: Path, tmp_path: Path, client: TestClient, point: str, run: list[str]
):
    (hooks / "a.py").write_text(f"def {point}(t):\n    raise ConnectionError('offline')\n")
    server.start_loading()
    assert client.post("/transcribe", content=SPEECH).status_code == 200
    assert errors(tmp_path) == [f"{point} in a.py:2: ConnectionError: offline"]
    assert (tmp_path / "log.txt").exists() == (point == "on_done")
    # The recorder sorts after a.py, so it sees only the phases before the failing one.
    assert [c[0] for c in calls(hooks)] == ["on_transcribed", "on_cleaned", *run[:-1]]


@pytest.mark.parametrize("point", ["on_sent", "on_done"])
def test_hook_returning_a_wrong_type_after_the_reply_is_recorded(
    hooks: Path, tmp_path: Path, client: TestClient, point: str
):
    (hooks / "a.py").write_text(f"def {point}(t): return {{}}\n")
    server.start_loading()
    assert client.post("/transcribe", content=SPEECH).status_code == 200
    message = f"{point} in a.py: TypeError: {point} returned dict, not str"
    assert errors(tmp_path) == [message]
    assert (tmp_path / "log.txt").exists() == (point == "on_done")
    ran = ["on_transcribed", "on_cleaned", *(["on_sent"] if point == "on_done" else [])]
    assert [c[0] for c in calls(hooks)] == ran


def test_on_done_returning_a_string_changes_nothing(
    hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "a.py").write_text("def on_done(t): return 'other'\n")
    server.start_loading()
    assert client.post("/transcribe", content=SPEECH).status_code == 200
    assert errors(tmp_path) == []
    assert (tmp_path / "log.txt").read_text() == "We should meet on Friday."


def test_on_error_returning_empty_gives_500_with_empty_detail(
    hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "a.py").write_text(
        "def on_transcribed(t):\n    raise ValueError('no')\n\ndef on_error(e):\n    return ''\n"
    )
    server.start_loading()
    response = client.post("/transcribe", content=SPEECH)
    assert (response.status_code, response.json()) == (500, {"detail": ""})
    assert errors(tmp_path) == []


def test_on_error_message_is_the_detail(hooks: Path, tmp_path: Path, client: TestClient):
    (hooks / "a.py").write_text(
        "def on_transcribed(t):\n    raise ValueError('no')\n\n"
        "def on_error(e):\n    return f'Oops,\\n{e}'\n"
    )
    server.start_loading()
    assert client.post("/transcribe", content=SPEECH).json() == {"detail": "Oops, no"}
    assert errors(tmp_path) == ["Oops, no"]


def test_503_while_models_are_not_loaded_is_left_alone(fakes: Fakes, hooks: Path, tmp_path: Path):
    (hooks / "a.py").write_text("def on_error(e):\n    return 'from on_error'\n")
    fakes.config = Config(stt_engine="vosk")
    with TestClient(server.app) as client:
        wait_for_load()
        response = client.post("/transcribe", content=SPEECH)
    assert (response.status_code, response.json()) == (
        503,
        {"detail": "ValueError: unknown stt.engine 'vosk'"},
    )
    assert errors(tmp_path) == ["ValueError: unknown stt.engine 'vosk'"]  # the load's only


def test_on_error_can_keep_a_failure_after_the_reply_out_of_errors_txt(
    hooks: Path, tmp_path: Path, client: TestClient
):
    (hooks / "archive.py").write_text(
        "import urllib.error\n\n"
        "def on_done(t):\n    raise urllib.error.URLError(ConnectionRefusedError())\n"
    )
    (hooks / "offline.py").write_text(
        "def on_error(e):\n"
        "    if isinstance(getattr(e, 'reason', e), ConnectionError):\n"
        "        return ''\n"
    )
    server.start_loading()
    assert client.post("/transcribe", content=SPEECH).status_code == 200
    assert (tmp_path / "log.txt").exists()
    assert errors(tmp_path) == []
