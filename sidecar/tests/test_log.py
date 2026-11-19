import re
from pathlib import Path

import pytest

from slopr_sidecar import lifecycle
from slopr_sidecar.lifecycle import write_error, write_log


@pytest.fixture
def log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Write texts to a temporary log.txt and return what it holds."""
    monkeypatch.setattr(lifecycle, "LOG", tmp_path / "log.txt")

    def dictate(*texts: str) -> str:
        for text in texts:
            write_log(text)
        return (tmp_path / "log.txt").read_text("utf-8")

    return dictate


def test_entries_are_separated_by_one_blank_line(log):
    assert log("Example.", "Second example.", "Third example.") == (
        "Third example.\n\nSecond example.\n\nExample."
    )


def test_keeps_the_newest_100_on_top(log):
    assert log(*map(str, range(101))).split("\n\n") == list(map(str, range(100, 0, -1)))


def test_multi_paragraph_text_is_flattened(log):
    assert log("First paragraph.\n\nSecond  one.\n", "Next.") == (
        "Next.\n\nFirst paragraph. Second one."
    )


def test_empty_existing_log_gives_no_blank_entry(log, tmp_path: Path):
    (tmp_path / "log.txt").touch()
    assert log("Only.") == "Only."


def test_trailing_newline_from_an_editor_gives_no_extra_blank_line(log, tmp_path: Path):
    (tmp_path / "log.txt").write_text("Two.\n\nOne.\n")
    assert log("Three.") == "Three.\n\nTwo.\n\nOne."


def test_blank_text_writes_nothing(log):
    assert log("One.", "  ") == "One."


def test_text_is_utf8(log, tmp_path: Path):
    assert log("Café, naïve, 日本語.") == "Café, naïve, 日本語."
    assert (tmp_path / "log.txt").read_bytes() == "Café, naïve, 日本語.".encode()


@pytest.fixture
def errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Write messages to a temporary errors.txt and return its entries."""
    monkeypatch.setattr(lifecycle, "ERRORS", tmp_path / "errors.txt")

    def fail(*messages: str) -> list[str]:
        for message in messages:
            write_error(message)
        return (tmp_path / "errors.txt").read_text("utf-8").split("\n\n")

    return fail


def test_error_entries_have_the_time_in_front(errors):
    [entry] = errors("cleanup model: TimeoutError")
    assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d cleanup model: TimeoutError", entry)


def test_errors_keep_the_newest_50_on_top_one_line_each(errors):
    entries = errors(*map(str, range(50)), "multi\nline")
    assert [entry[17:] for entry in entries] == ["multi line", *map(str, range(49, 0, -1))]


def test_failed_error_write_only_goes_to_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    monkeypatch.setattr(lifecycle, "ERRORS", tmp_path / "missing/errors.txt")
    write_error("speech recognition: RuntimeError")
    assert "errors.txt write failed" in caplog.text
