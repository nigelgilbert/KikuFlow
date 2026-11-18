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

No human check was needed: no Fix item was split or low confidence.

## Work items (pass 0)

Sidecar (`sidecar/`, `scripts/`):

| # | Item | What landed | Commits |
| --- | --- | --- | --- |
| 1 | Scaffold and config | uv project, Python 3.14.10 pinned, frozen-dataclass config read with `tomllib`, plan's schema and defaults | `545c42b` |
| 2 | Transcription | parakeet and whisper engines by config; body is 16-bit WAV (by RIFF header) or raw float32 LE PCM | `a360a5f`, `52665da` |
| 3 | Cleanup and safety check | mlx-lm, greedy, thinking off; simplewords with its `system_v2.txt` loaded from the repo, utter with its own prompt; `is_plausible` falls back to raw | `c724301` |
| 4 | HTTP server | `/health`, `/transcribe?cleanup=`, `/reload`; models loaded once on one worker thread and warmed up | `9edb629`, `51b79dc` |
| 5 | Bootstrap script | `scripts/bootstrap.sh`: uv installs the pinned Python and the venv in Application Support; idempotent | `c6a0e0e` |
| 6 | Contract doc | `sidecar/README.md` | `41eaaa1` |

App (`app/`, root `README.md`):

| # | Item | What landed | Commits |
| --- | --- | --- | --- |
| 7 | Package, bundle script, menu bar item | SwiftPM executable, `app/bundle.sh`, status icon per state, menu (cleanup toggle, open config, about, quit), About with the Parakeet CC-BY-4.0 credit | `4f76b30` |
| 8 | Sidecar manager | runs bootstrap, launches the sidecar, polls `/health`, restarts with backoff, stops it on quit, shows load errors | `ce3f5ea` |
| 9 | Global hotkey | listen-only CGEvent tap, Right Option only, fires on state change | `15678c3` |
| 10 | Audio capture | AVAudioEngine tap converted to 16 kHz mono float32 in memory, with a level for the waveform | `28cebed` |
| 11 | HUD | non-activating NSPanel: waveform, spinner, then the text | `32e135b` |
| 12 | Transcribe and paste | POST on release; save pasteboard, write, ⌘V via CGEvent, restore; toast with "Press ⌘V" when paste can't be sent | `710bfce` |
| 13 | Permissions and README | Accessibility and Microphone prompts, an "Allow …" menu item while one is missing, root README | `5bceb7d` |

## Fix pass (pass base 494a875)

All 11 items were sent; all were folded in with no pushback.

| Item | Result | Commits |
| --- | --- | --- |
| Fix 1 audio tap crash | `@Sendable` on the tap block. A scratch test through the real `installTap` and microphone trapped (SIGTRAP) before and passed after with 16 000 samples for 1 s. No test committed: it needs microphone hardware, and a manual-rendering test would mean injecting the engine. | `b9ac245` |
| (extra) | The same annotation on the `AVCaptureDevice.requestAccess` handlers. Precaution; not reproduced. | `36bb713` |
| Fix 2 orphaned sidecar | Sidecar thread exits the process when its parent changes. `kill -9` of the app: sidecar gone in about 0.5 s. | `de96eda` |
| Fix 3 bad config, port agreement | Port is the sidecar's first argument; the app reads it once for URL and launch. Malformed TOML and a wrong-type value both show as the menu's error. | `baf8d66`, `a29449c` |
| Fix 4 hotkey resync | After re-enabling the tap, state is re-read with `CGEventSource.keyState` for Right Option (used instead of `flagsState & 0x40`, whose left/right bits the headers don't promise). By reading, not reproduced. | `4cd3101` |
| Fix 5 whisper alone | `stt.model` defaults by engine; the written config and README leave the model line out. | `7db8dd3`, `fb6651a` |
| Nit 6 stale load state | Models and error set together on each outcome. | `b575e9d` |
| Nit 7 whisper preload | Removed. | `d047c69` |
| Nit 8 config types | `TypeError` when a value's type differs from the default's. | `ad9b517` |
| Nit 9 paste keycode | README sentence. | `ec01235` |
| Nit 10 transient clipboard | `org.nspasteboard.TransientType` written with the text. | `7b778c0` |
| Nit 11 Input Monitoring | README line. | `79ed671` |

The fix pass was not itself reviewed (one review requested).

## Open items

- **Needs a person at the keyboard; not verified by any run:** holding Right Option with real speech through the whole flow; the first microphone prompt; granting Accessibility and a real ⌘V paste into other apps with the clipboard restored; Left Option staying inert; the look of the menu, HUD and About panel; HUD position on notched and multi-screen setups.
- **Default cleanup model is gated on Hugging Face.** It needs the terms accepted and a token in `~/.cache/huggingface/token`. Done on this machine; anyone else building it hits the same step. The README covers it.
- **Config edits need an app relaunch.** Nothing in the app calls `/reload`, and a failed load stays failed until relaunch (review candidate 5, Wontfix).
- **Latency target unmeasured at 10 s.** About 75 ms transcription and 95 ms cleanup on a 5-second clip, against targets of 300 ms and 700 ms for 10 seconds.
- **Cleanup models are limited to the plan's two**, because each needs its own prompt shape; any other `cleanup.model` is rejected at load.
- **Safety check limit:** an answer that reuses the question's words can pass the word-overlap check.
- **Asked during the run, not built:** bundling the models into the app so no model download is needed. Also, the Hugging Face library contacts the hub on each start unless offline mode is set.
- **No committed test drives the real audio tap**, so the Fix 1 class of crash isn't guarded by the suite.

## Tests

- `cd sidecar && uv run pytest -q`: 21 passed. `uv run ruff check .`: clean. `uv run pyright`: 0 errors.
- `swift build --package-path app`: Build complete, no warnings. `sh app/test.sh`: 4 tests passed (plain `swift test` runs nothing under Command Line Tools without Xcode).
- Real-model smoke, default config: ready; "Um, so I think we should, uh, meet on Thursday. No wait, Friday at noon works better." came back as "So I think we should meet on Friday at noon."
