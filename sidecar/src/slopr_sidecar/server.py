"""HTTP server: loads the models in the background and serves /health, /transcribe, /reload."""

import asyncio
import logging
import os
import sys
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, Request

from .cleanup import Cleaner, is_plausible, load_cleaner
from .config import Config, load_config
from .stt import SAMPLE_RATE, Transcriber, decode_audio, load_transcriber

log = logging.getLogger("uvicorn.error")

# All model work (loading and inference) runs on this one thread, one job at a time.
executor = ThreadPoolExecutor(max_workers=1)


@dataclass(frozen=True)
class Models:
    config: Config
    transcribe: Transcriber
    clean: Cleaner | None


@dataclass
class State:
    models: Models | None = None
    error: str | None = None


state = State()


def load_models() -> None:
    try:
        config = load_config()
        transcribe = load_transcriber(config.stt_engine, config.stt_model)
        clean = load_cleaner(config.cleanup_model) if config.cleanup_enabled else None
        # One throwaway pass each, so the first dictation doesn't pay for kernel compilation.
        transcribe(np.zeros(SAMPLE_RATE, np.float32))
        if clean:
            clean("Hello there.")
    except Exception as e:
        log.exception("model load failed")
        state.error = f"{type(e).__name__}: {e}"
        return
    state.models = Models(config, transcribe, clean)


def start_loading() -> None:
    state.models, state.error = None, None
    executor.submit(load_models)


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_loading()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    m = state.models
    return {
        "ready": m is not None,
        "error": state.error,
        "stt_engine": m.config.stt_engine if m else None,
        "stt_model": m.config.stt_model if m else None,
        "cleanup_model": m.config.cleanup_model if m and m.clean else None,
    }


def run(audio: np.ndarray, cleanup: bool) -> dict:
    m = state.models
    if m is None:
        raise HTTPException(503, state.error or "models are loading")
    start = time.perf_counter()
    # A tap shorter than 0.1 s holds no speech.
    raw = m.transcribe(audio) if len(audio) >= SAMPLE_RATE // 10 else ""
    transcribed = time.perf_counter()
    clean = raw
    if cleanup and m.clean and raw:
        candidate = m.clean(raw)
        if is_plausible(raw, candidate):
            clean = candidate
    cleaned = time.perf_counter()
    return {
        "raw": raw,
        "clean": clean,
        "timings": {
            "stt_ms": round((transcribed - start) * 1000),
            "cleanup_ms": round((cleaned - transcribed) * 1000),
        },
    }


@app.post("/transcribe")
async def transcribe(request: Request, cleanup: bool = True) -> dict:
    try:
        audio = decode_audio(await request.body())
    except (ValueError, EOFError, wave.Error) as e:
        raise HTTPException(400, str(e)) from e
    return await asyncio.get_running_loop().run_in_executor(executor, run, audio, cleanup)


@app.post("/reload")
async def reload() -> dict:
    start_loading()
    return await health()


def exit_when_orphaned() -> None:
    """Exit once the launching app is gone (crash or force quit), freeing the port and memory."""
    parent = os.getppid()
    while os.getppid() == parent:
        time.sleep(1)
    os._exit(0)


def main() -> None:
    """`slopr-sidecar [PORT]`: the app passes PORT; run by hand, it comes from the config."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else load_config().port
    threading.Thread(target=exit_when_orphaned, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port)
