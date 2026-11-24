from pathlib import Path

import pytest

from kiku_sidecar.vocabulary import load_corrector, read_terms

TERMS = ["Claude", "Mac"]


def test_terms_are_one_per_line_without_blank_lines_or_surrounding_spaces(tmp_path: Path):
    (tmp_path / "vocabs.txt").write_text("  Claude \n\n\t\nMac\nmacOS Sequoia  \n")
    assert read_terms(tmp_path / "vocabs.txt") == ["Claude", "Mac", "macOS Sequoia"]


def test_a_byte_order_mark_is_not_part_of_the_first_term(tmp_path: Path):
    (tmp_path / "vocabs.txt").write_text("Claude\nMac\n", encoding="utf-8-sig")
    assert read_terms(tmp_path / "vocabs.txt") == ["Claude", "Mac"]


def test_a_file_that_is_not_utf8_is_an_error_naming_it(tmp_path: Path):
    (tmp_path / "vocabs.txt").write_bytes("Café\n".encode("latin-1"))
    with pytest.raises(ValueError, match=f"{tmp_path / 'vocabs.txt'} is not UTF-8 text"):
        read_terms(tmp_path / "vocabs.txt")


def test_missing_file_is_no_vocabulary(tmp_path: Path):
    assert read_terms(tmp_path / "vocabs.txt") == []


def test_no_terms_changes_nothing():
    assert load_corrector([])("claude on a mac") == "claude on a mac"


@pytest.mark.parametrize(
    ("heard", "corrected"),
    [
        ("terminal, start claude", "terminal, start Claude"),
        ("mac, open terminal.", "Mac, open terminal."),
        ("MAC dark mode", "Mac dark mode"),
        ("ask CLAUDE about my mac.", "ask Claude about my Mac."),
        ("is that claude's?", "is that Claude's?"),
    ],
)
def test_exact_matches_are_spelled_as_listed(heard: str, corrected: str):
    assert load_corrector(TERMS)(heard) == corrected


@pytest.mark.parametrize(
    "sentence",
    [
        "Open the map of the city.",
        "The files are in the cloud.",
        "She called me yesterday.",
        "It is cold outside.",
        "This machine is fast.",
        "Claudette and Macintosh are different words.",
        "Mac and Claude are already right.",
    ],
)
def test_other_words_come_back_unchanged(sentence: str):
    assert load_corrector(TERMS)(sentence) == sentence


def test_multi_word_terms_match_and_the_longer_one_wins():
    correct = load_corrector(["Mac", "Mac OS X", "Visual Studio Code"])
    assert correct("mac os x on my mac") == "Mac OS X on my Mac"
    assert correct("open visual studio code") == "open Visual Studio Code"
    assert correct("open visual studio") == "open visual studio"


def test_terms_are_literal_text_not_patterns():
    correct = load_corrector(["C++", "a.b", "(x)"])
    assert correct("i write c++ daily") == "i write C++ daily"
    assert correct("axb and a.b") == "axb and a.b"
    assert correct("call (X) now") == "call (x) now"


def test_a_case_variant_that_lower_misses_is_still_corrected():
    # IGNORECASE matches the long s "ſ" to "s", and only casefold maps it back.
    assert load_corrector(["Mars"])("on marſ") == "on Mars"


def test_the_first_of_two_spellings_wins():
    assert load_corrector(["iPhone", "IPHONE"])("my iphone") == "my iPhone"
