from voicenote.skills.finance_meeting import manifest


def test_finance_skill_declares_sensitive_semantic_fields() -> None:
    loaded = manifest()

    assert loaded.name == "finance_meeting"
    assert "financial_metric" in loaded.semantic_fields
    assert "risk" in loaded.semantic_fields
    assert "action_item" in loaded.semantic_fields

