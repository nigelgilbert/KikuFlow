# Factory report: mvp, run 1

- Work file: `docs/plan.md` (snapshot of https://claude.ai/artifact/CZyBTMU8j2Qs2z1fs1uY9B at rev 14)
- Branch `mvp`, base `f3513fa`
- Reviews: 1. Adversary: astra.
- Implementers: one for `sidecar/` and `scripts/`, one for `app/` and the root `README.md`.

## Review 1 trimmed list (range f3513fa..5bceb7d)

21 candidates, 11 items kept (5 Fix, 6 Nit; candidates 3 and 6 merged), 9 Wontfix, 0 Split. Adversary astra, 1 exchange after the independent first call.

### Fix

1. **Audio tap crashes on first buffer** — `app/Sources/SloprFlow/Recorder.swift:14`. The tap closure is formed in a `@MainActor` method under Swift 6 and the tap block type is not Sendable, so it inherits main-actor isolation and traps when AVFoundation calls it on the audio thread. Reproduced by the reviewer (SIGTRAP 5/5) and by the filter (3/3; exit 0 with `@Sendable`). Fix: `input.installTap(onBus: 0, bufferSize: 1024, format: format) { @Sendable buffer, _ in ... }`; add a manual-rendering test only if it needs no restructuring of `Recorder`. Confidence: high.
2. **Orphaned sidecar after app crash or force quit** — `app/Sources/SloprFlow/Sidecar.swift:65-72`, `sidecar/src/slopr_sidecar/server.py:22,62-65`. Only `applicationWillTerminate` stops the child. An orphan holds the port and the models; on relaunch the app reads the orphan's `/health` as Ready while each new sidecar starts a model load before its bind fails. Fix: a daemon thread in the sidecar that calls `os._exit` when `os.getppid()` changes from its value at start. No port preflight. Confidence: high.
3. **Bad config gives a silent restart loop; Swift and Python can disagree on the port** — `server.py:122-123`, `Sidecar.swift:10,66-69`, `app/Sources/SloprFlow/Config.swift:26-39`. `main()` calls `load_config()` unguarded, so bad TOML kills the sidecar before `/health` exists; the hand-rolled Swift parser can read a different port than `tomllib`. Fix: Swift reads the port once and passes it to the sidecar at launch; `main()` uses that argument and falls back to `load_config().port` only when run by hand, so a bad config reaches `load_models`' existing try/except and shows as a `/health` error. No stderr pipe. Confidence: high (medium for the port-agreement half).
4. **Hotkey state stuck after the tap is re-enabled** — `app/Sources/SloprFlow/Hotkey.swift:31-34`. `down` is not reconciled on `tapDisabledBy*`; a missed release leaves the mic recording and swallows the next press. Fix: after `tapEnable`, if `down` and `CGEventSource.flagsState(.combinedSessionState)` lacks `0x40`, set `down = false` and call `onChange(false)`. Confidence: high (by reading, not reproduced).
5. **`engine = "whisper"` alone fails at load** — `sidecar/src/slopr_sidecar/config.py:13`, `Config.swift:10`, `README.md:47`. Changing only the engine keeps the parakeet model id. Fix: default `stt_model` by engine in `load_config` (whisper: `mlx-community/whisper-large-v3-turbo`) and update the test; or, cheaper, extend the comment in `Config.swift:10` and `README.md:47` to say the model must change too. Confidence: high.

### Nit

6. **Stale state from overlapping loads** — `server.py:50-54`. Reachable only by manual `/reload`. Fix: write both fields on each outcome (`models, error = Models(...), None` on success; `None, msg` on failure). No generation counter. Confidence: medium.
7. **Redundant whisper preload** — `sidecar/src/slopr_sidecar/stt.py:10,41`. The warm-up already loads the model. Fix: drop the line and the `ModelHolder` import. Confidence: high.
8. **No type check on config values** — `config.py:19-29`. `enabled = "false"` is truthy; a string port passes through. Fix: at most one loop raising `TypeError` when `type(value) is not type(default)`. No schema. Confidence: medium.
9. **Paste keycode is positional** — `app/Sources/SloprFlow/Paste.swift:15`. Wrong shortcut on Dvorak-style layouts only. Fix: one README line. Confidence: medium.
10. **Dictations recorded by clipboard managers** — `Paste.swift:11`. Fix: `pasteboard.setData(Data(), forType: .init("org.nspasteboard.TransientType"))` after `setString`. Confidence: high.
11. **Input Monitoring not mentioned** — `Hotkey.swift:15-17`, `README.md:31`. Fix: one README sentence. Confidence: low (prompt behaviour not confirmed).

### Wontfix

- Candidate 5 (`.failed` is final): the README documents quit and reopen after editing config; the plan asks only for restart on crash.
- Candidate 7 (pasteboard snapshot cost, 0.5 s restore): the plan specifies save, paste, restore after a short delay; no proposed mitigation is correct and cheap.
- Candidate 9 (whisper hallucination on silence): mlx-whisper already applies `no_speech_threshold` and `logprob_threshold`; an RMS cutoff risks dropping quiet speech.
- Candidate 10 (503 for a transcribe queued across `/reload`): manual-only path; keeping both model sets costs memory.
- Candidate 11 (defaults in three places): no drift shown; a shared resource file adds packaging for five keys.
- Candidate 14 (float32 WAV rejected): 16-bit is documented and the app sends raw float32.
- Candidate 15 (truncated cleanup output): the 2.0 word-ratio check rejects nearly all truncations; detection needs a `stream_generate` loop.
- Candidate 20 (`engine.start()` per press): unmeasured; an always-on engine keeps the mic indicator lit.
- Candidate 21 (Task per audio buffer): main-actor delivery is needed either way; no cost shown.

### Split

None.
