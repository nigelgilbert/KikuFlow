# Factory report: feature/vocab, run 1

- Work file: `docs/vocabulary-plan.md`
- Base commit: `374c730` (the plan itself)
- Reviews: 1. Adversary: sol.

## Scope

Steps 1 and 2 of the plan, its tests and its docs. Step 3, the sound-alike matching, is not built: it needs the confidence measurements from the user's own recordings, which step 1's script exists to produce.

## Work items

| Item | What landed | Commit |
| --- | --- | --- |
| 1. Measurement script | `sidecar/scripts/word_confidence.py` prints each word Parakeet heard with its confidence | `fa7365c` |
| 2. Vocabulary module | `sidecar/src/kiku_sidecar/vocabulary.py` reads `vocabs.txt` and spells an exact whole-word match as listed | `3fe06b6` |
| 3. Sidecar plumbing | The vocabulary runs in `process` before the `on_transcribed` hooks; `raw` stays what speech recognition heard | `100dc89` |
| 4. Whisper hint | With Whisper, the terms go in as `initial_prompt`, joined with ", " | `90abca0` |
| 5. Menu item | "Open Vocabulary" with ⌘V, below "Open Config"; it creates the file if missing | `ac2c3bb` |
| 6. Tests | Landed with items 2 to 5, so every commit passes | with each item |
| 7. Docs | `docs/customization.md`, `docs/hooks.md`, `README.md`, `sidecar/README.md` | `99254e1` |

## Review 1: trimmed list

Range `374c730..99254e1`. 19 candidates, 13 kept (2 Fix, 11 Nit), 6 Wontfix, 2 Split. Two exchanges with sol.

### Fix

1. **Whisper with a vocabulary turns silence into invented text, which is pasted.**
   - `sidecar/src/kiku_sidecar/stt.py:45-48`, `docs/customization.md:77`, `sidecar/README.md:79`
   - Problem: on `mlx-community/whisper-tiny`, one and three seconds of silence return nothing with no prompt, and invented text with `initial_prompt="Claude, Mac"`. The prompt lowers the model's no-speech score below its 0.6 threshold. Not tested on the default `whisper-large-v3-turbo`.
   - Fix: add a caveat to the Whisper paragraph of "Your vocabulary" in `docs/customization.md` and to the Vocabulary paragraph of `sidecar/README.md`.
   - Open for the user: whether to add a code guard. No cheap remedy worked reliably on tiny, and a lower no-speech threshold needs measuring on large-v3-turbo first.
   - Confidence: high for the defect and the caveat.
2. **`word_confidence.py` lets a punctuation token set a word's confidence.**
   - `sidecar/scripts/word_confidence.py:39-46`
   - Problem: Parakeet has standalone `,`, `.` and `?` tokens. They join the preceding word, and the minimum can report the comma's confidence as that of "Mac,".
   - Fix: keep punctuation in the printed text, but take the minimum over the tokens that hold a word character, falling back to all tokens when none does. Say so in the docstring.
   - Confidence: high.

### Nit

3. **⌘V on "Open Vocabulary" matches the app's own paste keystroke.** `app/Sources/KikuFlow/App.swift:66`, `Paste.swift:24-32`. If the menu is open when a dictation's reply arrives, the posted ⌘V may open `vocabs.txt`. That paste was already lost in this state before the branch. Reasoned from AppKit behaviour, not run. The user chose ⌘V, so this is the user's call. Confidence: low.
4. **"The longer one wins" is overstated.** `docs/customization.md:75`, `sidecar/README.md:79`. The earliest match wins, and length only breaks a tie at the same start. Fix: reword both. Confidence: medium.
5. **A UTF-8 BOM breaks the first term.** `vocabulary.py:20`. Fix: read with `utf-8-sig`. Confidence: medium.
6. **A `vocabs.txt` that is not UTF-8 fails the load without naming the file.** `vocabulary.py:20`. Fix: re-raise as a `ValueError` naming the path. Confidence: medium.
7. **The `verbatim.py` recipe says "word for word" but gets the `vocabs.txt` spelling.** `docs/hooks.md:137`. Fix: one clause. Confidence: medium.
8. **`re.IGNORECASE` and `.lower()` disagree for a few characters.** `vocabulary.py:48,53`. A match is left unchanged, never corrupted. Fix: key on `casefold()`. Confidence: low (split).
9. **A long list loses Whisper's hint for its first terms.** `stt.py:45`. Whisper keeps about the last 223 tokens of a prompt. Fix: one sentence in the docs. Confidence: high.
10. **`timings.stt_ms` now includes the vocabulary pass.** `server.py:126-128`. One regex substitution; safe to leave. Confidence: high.
11. **Unannotated fake in a test.** `sidecar/tests/test_stt.py:54`. Fix: annotate it. Confidence: high.
12. **`load_corrector` loads nothing.** `vocabulary.py:38`. The name mirrors `load_cleaner`; safe to leave. Confidence: high.
13. **The script's default model is the built-in one, not the configured one.** `word_confidence.py:56`. Fix: say so in the docstring. Confidence: high.

### Wontfix

- Candidate 2: Whisper echoing the term list did not reproduce. The real part is Fix 1.
- Candidate 5: a double space inside a term is a typo in the file.
- Candidate 13: see Split.
- Candidate 16: duplicate terms in the prompt show no harm.
- Candidate 17: unmeasured guess about prompt style.
- Candidate 19: the two `vocabulary` error labels already differ.

### Split

- **Candidate 7 (Nit 8).** Filter: nit, since few characters are affected and nothing is corrupted. Sol: fix, since nothing limits matching to English, and it wants each pattern alternative bound to its spelling. Decision: nit.
- **Candidate 13 (Wontfix).** Filter: wontfix, since the script is throwaway and its docstring says WAV only. Sol: nit, since non-WAV bytes are read as raw audio and print bogus scores. Decision: wontfix.
