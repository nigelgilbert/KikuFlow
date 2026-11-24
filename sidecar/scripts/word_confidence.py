"""Print each word Parakeet hears in a recording, with its confidence.

Run it from `sidecar/` on one or more 16 kHz mono 16-bit WAV files:

    uv run python scripts/word_confidence.py mac1.wav mac2.wav
    uv run python scripts/word_confidence.py --model mlx-community/parakeet-tdt-0.6b-v2 mac1.wav

To make such a file from any recording: `afconvert -f WAVE -d LEI16@16000 -c 1 in.m4a out.wav`.

Each file prints its name, then one word per line: the confidence, from 0 to 1, and the word.
Parakeet scores sub-word tokens, and a token that starts with a space starts a new word.
A word's confidence is the lowest of its tokens' confidences, since a word is only as sure as
its least sure piece.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import mlx.core as mx
from parakeet_mlx import from_pretrained
from parakeet_mlx.alignment import AlignedToken
from parakeet_mlx.audio import get_logmel

from kiku_sidecar.config import STT_MODELS
from kiku_sidecar.stt import decode_audio


@dataclass(frozen=True)
class Word:
    text: str
    confidence: float


def group_into_words(tokens: list[AlignedToken]) -> list[Word]:
    """Return the words the tokens spell, each with its lowest token confidence."""
    groups: list[list[AlignedToken]] = []
    for token in tokens:
        starts_word = token.text.startswith(" ")
        if starts_word or not groups:
            groups.append([])
        groups[-1].append(token)
    words = []
    for group in groups:
        text = "".join(token.text for token in group).strip()
        confidence = min(token.confidence for token in group)
        words.append(Word(text, confidence))
    return words


def parse_arguments() -> argparse.Namespace:
    """Return the WAV paths and the model named on the command line."""
    description = "Print each word Parakeet hears, with its confidence."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("wavs", nargs="+", type=Path, help="16 kHz mono 16-bit WAV files")
    parser.add_argument("--model", default=STT_MODELS["parakeet"], help="a Parakeet model")
    return parser.parse_args()


def main() -> None:
    """Print the words and confidences of each WAV named on the command line."""
    arguments = parse_arguments()
    parakeet = from_pretrained(arguments.model)
    for path in arguments.wavs:
        audio = decode_audio(path.read_bytes())
        mel = get_logmel(mx.array(audio), parakeet.preprocessor_config)
        result = parakeet.generate(mel)[0]
        print(path)
        for word in group_into_words(result.tokens):
            print(f"{word.confidence:.3f}  {word.text}")


if __name__ == "__main__":
    main()
