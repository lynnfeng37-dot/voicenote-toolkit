from voicenote.core.correction import CorrectionPolicy, apply_corrections
from voicenote.core.diff import render_correction_audit_markdown
from voicenote.core.schemas import CorrectionProposal, RawTranscript, TextSpan


def test_audit_markdown_includes_decision_and_sensitivity(raw_transcript: RawTranscript) -> None:
    corrected = apply_corrections(
        raw_transcript,
        (
            CorrectionProposal(
                segment_id="seg-1",
                original="夏普币率",
                corrected="夏普比率",
                span=TextSpan(start=4, end=8),
                confidence=0.97,
                reason="Terminology",
                category="financial_metric",
                sensitive=True,
            ),
        ),
        CorrectionPolicy(),
    )

    rendered = render_correction_audit_markdown(corrected)

    assert "apply_and_flag" in rendered
    assert "夏普币率" in rendered
    assert "yes" in rendered

