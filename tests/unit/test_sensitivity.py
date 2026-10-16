from voicenote.core.sensitivity import is_sensitive_correction


def test_numeric_change_is_sensitive_even_when_category_is_generic() -> None:
    assert is_sensitive_correction("10%", "40%", "asr_error") is True


def test_sensitive_category_is_case_insensitive() -> None:
    assert is_sensitive_correction("Apple", "AAPL", "Ticker_Symbol") is True


def test_ordinary_technical_term_is_not_automatically_sensitive() -> None:
    assert is_sensitive_correction("容器编排", "容器编排", "technical_term") is False

