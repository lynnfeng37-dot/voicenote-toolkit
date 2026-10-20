import pytest

from voicenote.core.correction import CorrectionPolicy, apply_corrections
from voicenote.core.review import collect_review_concerns
from voicenote.core.schemas import (
    CorrectionDecision,
    CorrectionProposal,
    RawTranscript,
    TextSpan,
    UncertainSpan,
)


@pytest.mark.parametrize(
    ("confidence", "decision"),
    [
        (0.99, CorrectionDecision.AUTO_APPLY),
        (0.95, CorrectionDecision.APPLY_AND_FLAG),
        (0.80, CorrectionDecision.RETAIN_UNCERTAIN),
    ],
)
def test_review_concerns_follow_correction_policy(
    raw_transcript: RawTranscript, confidence: float, decision: CorrectionDecision
) -> None:
    proposal = CorrectionProposal(
        segment_id="seg-1", original="夏普币率", corrected="夏普比率",
        span=TextSpan(start=4, end=8), confidence=confidence, reason="Review terminology",
        category="financial_metric", sensitive=True, evidence=("context",),
    )
    corrected = apply_corrections(raw_transcript, (proposal,), CorrectionPolicy())
    concerns = collect_review_concerns(corrected)
    assert corrected.corrections[0].decision == decision
    if decision == CorrectionDecision.AUTO_APPLY:
        assert concerns == ()
    else:
        assert len(concerns) == 1  # No duplicate from the matching UncertainSpan.
        assert concerns[0].decision == decision
        assert concerns[0].sensitive is True
        assert concerns[0].evidence == ("context",)
        assert concerns[0].current_text == (
            proposal.corrected
            if decision == CorrectionDecision.APPLY_AND_FLAG
            else proposal.original
        )


def test_imported_uncertainty_without_correction_record_is_preserved(
    raw_transcript: RawTranscript,
) -> None:
    corrected = apply_corrections(raw_transcript, (), CorrectionPolicy()).model_copy(update={
        "uncertainties": (UncertainSpan(
            segment_id="seg-1", text="夏普币率", span=TextSpan(start=4, end=8),
            confidence=0.5, reason="Unclear audio",
        ),),
    })
    concerns = collect_review_concerns(corrected)
    assert len(concerns) == 1
    assert concerns[0].proposed_text is None
    assert concerns[0].current_text == "夏普币率"
