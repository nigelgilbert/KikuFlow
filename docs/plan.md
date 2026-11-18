# Slopr Flow — Build Plan

Source: https://claude.ai/artifact/CZyBTMU8j2Qs2z1fs1uY9B (snapshot at rev 14, 2026-11-18).

Slopr Flow is a minimal, open-source, fully local Wispr Flow–style dictation tool for Apple Silicon Macs. Hold a key, speak, release, and cleaned-up text lands in whatever app has focus.

## Goals and non-goals

**Goals**

- Fully on-device, no cloud, no accounts.
- Quality comparable to Wispr Flow: accurate transcription plus an LLM cleanup pass (fillers removed, self-corrections applied, punctuation and casing fixed).
- Fast enough to feel instant on a short dictation.
- Open source throughout; models are user-selectable via config.
- Small enough to ship a working version one quickly.

**Non-goals for v1**

- Meeting recording, file transcription, system audio.
- True accessibility-API text injection (planned for v2).
- Windows or Linux.

## Architecture

Two processes:

1. **Swift menu-bar app** (the shell). Owns the global hotkey, microphone capture, the notch/HUD overlay, the clipboard paste, and the lifecycle of the sidecar.
2. **Python sidecar** (the brains). A tiny localhost HTTP server that accepts audio and returns cleaned text. Runs the speech model and the cleanup model via MLX.

The Swift app launches the sidecar on startup and talks to it over `http://127.0.0.1:<port>`. If the sidecar dies, the app restarts it.

Rationale: Swift gives native hotkeys, overlays, and permissions; Python gives access to the mature MLX model ecosystem without learning MLX Swift. The sidecar can later be swapped for in-process WhisperKit without touching the UI.

## Models

**Transcription (default): NVIDIA Parakeet TDT 0.6B v3** via the `parakeet-mlx` package.

- More accurate than Whisper large-v3 on English and about 25 European languages, and dramatically faster.
- CC-BY-4.0 license: include attribution in the app's About panel.
- Note from the Pomvox project: the same Parakeet weights score roughly 6.3% WER on one open-source runtime and roughly 2.5% on another. Benchmark `parakeet-mlx` against FluidAudio/CoreML on your own voice before settling.

**Cleanup (default): `ReFyneLabs/simplewords-dictation-cleanup-v3`** via `mlx-lm`.

- QLoRA fine-tune of Qwen3.5-2B, 8-bit, purpose-built for post-ASR dictation cleanup. Built for Pomvox.
- Use its frozen `system_v2.txt` prompt exactly as shipped, greedy decoding, thinking disabled.

**Cleanup (alternative, selectable): `devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit`**, Utter's Qwen3-1.7B fine-tune. Try both for a day and keep the one you prefer.

**Cleanup safety check.** Small general-purpose LLMs have been observed answering the dictated question or writing code instead of cleaning the text. Even with a fine-tune, verify the output: if it is wildly different in length or shares too few tokens with the raw transcript, fall back to the raw transcript. Make the cleanup pass toggleable.

## Python sidecar

Managed with **uv**. macOS does not ship a usable Python; on first launch the Swift app runs a bootstrap script that has uv install a pinned Python and create a venv in `~/Library/Application Support/SloprFlow/`.

**Dependencies:** `parakeet-mlx`, `mlx-whisper`, `mlx-lm`, `fastapi`, `uvicorn`, `numpy`.

**Endpoints**

- `GET /health` — returns ready status and loaded model names.
- `POST /transcribe` — body: 16 kHz mono PCM or WAV bytes; query: `cleanup=true|false`. Returns `{"raw": ..., "clean": ..., "timings": {...}}`.
- `POST /reload` — reloads models from config.

**Config file** (`config.toml` in Application Support):

```toml
[stt]
engine = "parakeet"   # or "whisper"
model = "mlx-community/parakeet-tdt-0.6b-v3"

[cleanup]
enabled = true
model = "ReFyneLabs/simplewords-dictation-cleanup-v3"

[server]
port = 48123
```

Load both models once at startup and keep them warm. Target: under 300 ms transcription and under 700 ms cleanup for a 10-second utterance on an M-series Pro.

## Swift app

**Components**

- **Menu bar item** with a status indicator (Ready, Listening, Thinking) and a small menu: toggle cleanup, open config, quit.
- **Global hotkey**, hold-to-talk by default. Suggested default: Right Option or Fn. Use a Carbon/CGEvent tap or a package such as `KeyboardShortcuts`.
- **Audio capture** with AVAudioEngine, resampled to 16 kHz mono float32, buffered in memory while the key is held.
- **Notch overlay / HUD** showing a waveform while listening and a spinner while processing. Evaluate an open-source notch UI package such as DynamicNotchKit; fall back to a plain floating NSPanel if it is fiddly.
- **Output (v1): clipboard and paste.** Save the current pasteboard, write the clean text, send Command-V via CGEvent, then restore the pasteboard after a short delay. Show a toast in the notch with the text and a "Press ⌘V" hint if paste appears to have failed.
- **Sidecar manager** that launches the Python process, waits on `/health`, and restarts it on crash.

**Permissions needed:** Microphone, Accessibility (for the synthetic Command-V keystroke).

## Flow

1. User presses and holds the hotkey. HUD appears, capture starts.
2. User releases. Capture stops, audio is posted to `/transcribe`.
3. Sidecar transcribes, runs cleanup, verifies, returns text.
4. App pastes the text and briefly shows it in the HUD.

## Reference projects to borrow from

- Pomvox — Parakeet plus the simplewords cleanup model, MIT. Read it for runtime benchmarks.
- MacParakeet — mature Swift app, GPL-3. Read it for hotkey, HUD, and paste handling.
- parakeet-rs — single-binary AppKit app with Qwen 3.5 2B cleanup via llama.cpp.
- VoicePop — SwiftUI HUD and honest latency metrics.
- OpenWhispr — the Electron "Wispr Flow alternative", cross-platform.
