# Plan: vocabulary file

## Goal

Words listed in `vocabs.txt` come out spelled as listed, before any hook sees the text. The first two terms are `Claude` and `Mac`.

## Background

Two mishearings keep happening with the Parakeet engine:

- "Mac, …" is transcribed as "Map …", so the `mac_commands.py` hook never fires. `log.txt` has two entries reading "Map open terminal."
- "Claude", as in "Terminal, start Claude", comes out wrong. The log holds no example, so the misheard spelling is not yet known.

Three facts shape the design:

- `parakeet-mlx` 0.7.0 has no way to bias the model toward given words. Whisper does, through the `initial_prompt` argument of `mlx_whisper.transcribe`.
- Both terms sound like ordinary words. "Claude" has the same sound code as "cloud", "called" and "cold", and "Mac" is one letter from "map". A matcher that rewrites every sound-alike would damage normal dictation.
- `parakeet-mlx` gives each token a `confidence` between 0 and 1 (`AlignedToken` in its `alignment.py`). The sidecar discards it today. Rewriting a sound-alike only when Parakeet was unsure of the word may make a bare list safe. This is not yet measured, so step 1 measures it.

## Decisions already made

- **File:** `vocabs.txt` in the Kiku Flow folder, `~/Library/Application Support/KikuFlow/`. One term per line. Blank lines are ignored, and a missing file means no vocabulary.
- **Menu:** "Open Vocabulary" with ⌘V, below "Open Config". It creates the file if missing, as `Config.open` does for `config.toml`.
- **Placement:** in `process` in `sidecar/src/kiku_sidecar/server.py`, between the transcribe call and the `on_transcribed` hooks. Every hook then receives corrected text.
- **Hooks:** the vocabulary is not exposed through the `kiku` package.
- **Reload:** edits take effect on "Reload Kiku Flow", like config edits.

## Step 1: measure before building the matcher

1. Write a throwaway script that runs Parakeet on a recording and prints each word with its confidence.
2. Record about ten utterances each of "Mac, …" and "Terminal, start Claude", plus ten sentences that really contain "map" and "cloud".
3. Compare the confidence of the misheard words with the confidence of the real ones.

The result decides step 3. If misheard words score clearly lower, use the confidence gate. If they do not, choose from the options under "Open decision".

## Step 2: file, menu and plumbing

- `sidecar/src/kiku_sidecar/vocabulary.py`: read the file and return a `correct` function, shaped like `load_cleaner` in `cleanup.py`.
- `server.py`: load it in `load_models`, add it to `Models`, and call it in `process`.
- `app/Sources/KikuFlow/Config.swift` and `App.swift`: the file's path, a function that opens it, and the menu item.
- First behaviour, safe without step 3: fix the casing of an exact whole-word match, so "claude" becomes "Claude" and "mac" becomes "Mac".
- `sidecar/src/kiku_sidecar/stt.py`: when the engine is Whisper, pass the terms as `initial_prompt`.

## Step 3: sound-alike matching

- Rewrite a word to a listed term when it sounds alike, is spelled closely, and Parakeet's confidence in it is below the threshold found in step 1.
- The transcriber must return words with their confidence instead of a plain string. This changes the `Transcriber` type in `stt.py` and its callers.
- A term under four letters matches only a word at edit distance one, and only under the confidence gate.
- Whisper reports no comparable per-word score through the current call, so with Whisper the sound-alike step is off and the `initial_prompt` does the work.

## Tests

- `sidecar/tests/test_vocabulary.py`:
  - File parsing: blank lines, surrounding spaces, a missing file.
  - Casing fixes on exact matches.
  - The matcher against the step 1 recordings, reduced to pairs of word and confidence.
  - Sentences that must come back unchanged: real uses of "map", "cloud", "called" and "cold".
- `app/Tests/KikuFlowTests/ConfigTests.swift`: the vocabulary file's path.

## Docs

- A "Your vocabulary" section in `docs/customization.md`, saying that the list nudges the output and does not guarantee it.
- A `vocabs.txt` row in that file's table of the Kiku Flow folder.

## Open decision

If step 1 shows that confidence does not separate the mishearings, a bare list cannot fix "Mac" or "Claude" on Parakeet. The choices then are:

- Switch to Whisper, where the list is a real hint to the model.
- Allow an optional `Mac: map` form on a line, accepting that every "map" becomes "Mac".
- Fix "Mac" in `mac_commands.py` alone by letting its prefix accept "Map". That is safe there, because the hook's model already answers "none" for text that is not a command.
