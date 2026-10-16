from voicenote.core.references import load_finance_terminology


def test_finance_terminology_is_loaded_as_validated_data() -> None:
    entries = load_finance_terminology()

    sharpe = next(entry for entry in entries if entry.canonical == "夏普比率")
    assert "Sharpe ratio" in sharpe.variants
    assert sharpe.sensitive is True

