import pytest

from slopr_sidecar.cleanup import is_plausible, load_cleaner

RAW = "um so I think we should uh meet on Thursday no wait Friday at noon works better"


def test_real_cleanup_passes():
    assert is_plausible(RAW, "I think we should meet on Friday at noon. That works better.")


def test_self_correction_that_drops_most_words_passes():
    raw = "Let's meet Thursday. No, no, wait, uh we'll meet Friday actually."
    assert is_plausible(raw, "Let's meet Friday.")


def test_length_blow_up_fails():
    assert not is_plausible("meet on Friday", "meet on Friday " * 4)


def test_answering_a_dictated_question_fails():
    raw = "how do I reverse a list in python"
    answer = "You can call the reverse method, or use slicing with a step of minus one."
    assert not is_plausible(raw, answer)


def test_empty_output_fails():
    assert not is_plausible(RAW, "")


def test_unsupported_model_fails_at_load():
    with pytest.raises(ValueError, match="unsupported cleanup.model"):
        load_cleaner("some/other-model")
