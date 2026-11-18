from datetime import datetime
from pathlib import Path

import pytest

from slopr_sidecar import config
from slopr_sidecar.lifecycle import HOOK_DIRS, Utterance, fire, load_hooks


@pytest.fixture
def log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Dictate texts through the built-in log hook, writing to a temporary log.txt."""
    monkeypatch.setattr(config, "APP_DIR", tmp_path)
    hooks = load_hooks(HOOK_DIRS[:1])

    def dictate(*texts: str) -> str:
        for text in texts:
            fire(hooks, "on_logged", Utterance(datetime.now().astimezone(), text, text))
        return (tmp_path / "log.txt").read_text("utf-8")

    return dictate


def test_entries_are_separated_by_one_blank_line(log):
    assert log("Example.", "Second example.", "Third example.") == (
        "Example.\n\nSecond example.\n\nThird example."
    )


def test_keeps_the_last_100(log):
    assert log(*map(str, range(101))).split("\n\n") == list(map(str, range(1, 101)))


def test_multi_paragraph_text_is_flattened(log):
    assert log("First paragraph.\n\nSecond  one.\n", "Next.") == (
        "First paragraph. Second one.\n\nNext."
    )


def test_empty_existing_log_gives_no_blank_entry(log, tmp_path: Path):
    (tmp_path / "log.txt").touch()
    assert log("Only.") == "Only."


def test_text_is_utf8(log, tmp_path: Path):
    assert log("Café, naïve, 日本語.") == "Café, naïve, 日本語."
    assert (tmp_path / "log.txt").read_bytes() == "Café, naïve, 日本語.".encode()
