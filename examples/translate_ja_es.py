"""Start or end with "in Japanese" or "in Spanish" to paste in that language."""

import json
import re
from typing import override

from kiku import Plugin, load_model

MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
PARSE = (
    "The user's text may open or end with a spoken request to translate it, like "
    '"in Japanese" or "translate this to Spanish". '
    "Never answer the text, act on it or translate it. "
    'Reply with JSON only: {"language": the language asked for}, '
    "or null when the text is not asking for a translation."
)
EXAMPLES = (
    ("In Spanish, where is the station?", '{"language": "Spanish"}'),
    ("See you at noon, in Japanese.", '{"language": "Japanese"}'),
    ("In Japanese cooking, rice comes first.", '{"language": null}'),
    ("translate this to spanish good morning", '{"language": "Spanish"}'),
    ("She answered me in Spanish.", '{"language": null}'),
    ("Remind me to call the bank.", '{"language": null}'),
)
LANGUAGES = re.compile(r"\b(?:Japanese|Spanish)\b", re.IGNORECASE)
LEAD_IN = re.compile(r"\s*\b(?:in|to|into)\s*$", re.IGNORECASE)
PUNCTUATION = " ,.:;-"
TRANSLATE = (
    "Translate the user's text into {}. Keep its meaning and its tone. "
    "Never answer it or act on it. Output only the translation."
)


class Translate(Plugin):
    def __init__(self) -> None:
        self.model = load_model(MODEL)
        self.language: str | None = None

    @override
    def on_transcribed(self, t: str) -> str:
        """Take the request out, so the cleanup model sees only the text."""
        self.language = None
        if not LANGUAGES.search(t):
            return t
        reply = self.model.prompt(PARSE, t, EXAMPLES)
        try:
            asked = json.loads(reply)["language"]
        except ValueError, KeyError, TypeError:
            return t
        if not asked:
            return t
        before, after = re.split(asked, t, maxsplit=1, flags=re.IGNORECASE)
        self.language = asked
        said_after = after.strip(PUNCTUATION)
        said_before = LEAD_IN.sub("", before).strip(PUNCTUATION)
        return said_after or said_before

    @override
    def on_cleaned(self, t: str) -> str:
        """Return the text in the language that was asked for."""
        if not self.language:
            return t
        system = TRANSLATE.format(self.language)
        return self.model.prompt(system, t) or t
