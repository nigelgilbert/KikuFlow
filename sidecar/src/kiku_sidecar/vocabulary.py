"""The vocabulary in ~/Library/Application Support/KikuFlow/vocabs.txt: words spelled as listed."""

import re
from collections.abc import Callable
from pathlib import Path

from .config import APP_DIR

VOCABULARY_FILE = APP_DIR / "vocabs.txt"

type Corrector = Callable[[str], str]


def read_terms(path: Path = VOCABULARY_FILE) -> list[str]:
    """Return the terms in the file at `path`, one per line, or none when it is missing.

    Surrounding whitespace is stripped, and blank lines are left out.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    lines = (line.strip() for line in text.splitlines())
    return [term for term in lines if term]


def whole_words_pattern(terms: list[str]) -> re.Pattern[str]:
    """Return a case-insensitive pattern for any of `terms` as whole words, longest first.

    Each term is literal text. Trying the longest first lets "Mac OS" win over "Mac".
    """
    longest_first = sorted(terms, key=len, reverse=True)
    alternatives = "|".join(map(re.escape, longest_first))
    # Lookarounds rather than \b, so a term that ends in a symbol, like "C++", still matches.
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.IGNORECASE)


def load_corrector(terms: list[str]) -> Corrector:
    """Return a function that spells each whole-word match of a term, in any case, as listed.

    With no terms it returns the text unchanged. Of two terms that differ only in case, the first
    listed wins.
    """
    if not terms:
        return lambda text: text
    spellings: dict[str, str] = {}
    for term in terms:
        spellings.setdefault(term.lower(), term)
    pattern = whole_words_pattern(terms)

    def listed_spelling(match: re.Match[str]) -> str:
        heard = match[0]
        return spellings.get(heard.lower(), heard)

    def correct(text: str) -> str:
        return pattern.sub(listed_spelling, text)

    return correct
