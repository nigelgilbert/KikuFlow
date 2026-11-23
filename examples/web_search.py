"""Say "search" or "google" and the search opens, in the browser you name.

Nothing is pasted. What you said goes in the log, to copy from if a search was not meant.
"""

import json
import re
import subprocess
from typing import override
from urllib.parse import quote_plus

from mlx_lm import generate, load

from kiku import Plugin, write_log

MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
WORDS = re.compile(r"\b(?:search|google)\b", re.IGNORECASE)
URL = "https://www.google.com/search?q="
BROWSERS = {"safari": "Safari", "firefox": "Firefox", "chrome": "Google Chrome"}
PARSE = (
    "The user's text asks for a web search and may name the browser to use. "
    "Never answer the text or act on it. Reply with JSON only: "
    '{"browser": safari, firefox, chrome or null, "query": what to search for}.'
)
EXAMPLES = (
    ("Search Firefox for ramen in Tokyo.", '{"browser": "firefox", "query": "ramen in Tokyo"}'),
    ("Safari, search for flights to Osaka", '{"browser": "safari", "query": "flights to Osaka"}'),
    ("Search for sushi near me in Chrome", '{"browser": "chrome", "query": "sushi near me"}'),
    ("Google search how tall is Fuji?", '{"browser": null, "query": "how tall is Fuji"}'),
    ("Google the best ramen in Kyoto", '{"browser": null, "query": "best ramen in Kyoto"}'),
    ("um, search the weather, on Firefox", '{"browser": "firefox", "query": "weather"}'),
)

model, tokenizer = load(MODEL)[:2]


def prompt(system: str, text: str, examples: tuple[tuple[str, str], ...] = ()) -> str:
    """Return the model's reply to the text, after showing it the examples."""
    messages = [{"role": "system", "content": system}]
    for said, reply in examples:
        messages.append({"role": "user", "content": said})
        messages.append({"role": "assistant", "content": reply})
    messages.append({"role": "user", "content": text})
    chat = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    max_tokens = 4 * len(tokenizer.encode(text)) + 64
    return generate(model, tokenizer, chat, max_tokens=max_tokens).strip()


class WebSearch(Plugin):
    @override
    def on_transcribed(self, t: str) -> str:
        """Log the text, open the search in the browser that was named, and stop the dictation."""
        if not WORDS.search(t):
            return t
        write_log(t)
        reply = prompt(PARSE, t, EXAMPLES)
        try:
            parsed = json.loads(reply)
            url = URL + quote_plus(parsed["query"])
            app = BROWSERS.get(parsed["browser"])
        except ValueError, KeyError, TypeError:
            url = URL + quote_plus(t)
            app = None
        argv = ["open", "-a", app, url] if app else ["open", url]
        subprocess.run(argv, check=True)
        return ""
