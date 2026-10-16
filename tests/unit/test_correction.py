from __future__ import annotations

import pytest

from voicenote.core.correction import CorrectionPolicy, apply_corrections
from voicenote.core.schemas import (
    CorrectionDecision,
    CorrectionProposal,
    RawTranscript,
    TextSpan,
)
from voicenote.exceptions import CorrectionConflictError


def test_high_confidence_correction_is_applied_and_traced(raw_transcript: RawTranscript) -> None:
    proposal = CorrectionProposal(
        segment_id="seg-1",
        original="夏普币率",
        corrected="夏普比率",
        span=TextSpan(start=4, end=8),
        confidence=0.97,
        reason="Finance terminology and context",
        category="finance_term",
        evidence=("terminology:sharpe_ratio",),
    )

    result = apply_corrections(raw_transcript, (proposal,), CorrectionPolicy())

    assert result.raw_transcript.segments[0].text == "我们讨论夏普币率和百分之十的回报。"
    assert result.segments[0].corrected_text == "我们讨论夏普比率和百分之十的回报。"
    assert result.corrections[0].decision is CorrectionDecision.AUTO_APPLY


def test_sensitive_proposal_uses_stricter_threshold(raw_transcript: RawTranscript) -> None:
    proposal = CorrectionProposal(
        segment_id="seg-1",
        original="百分之十",
        corrected="百分之四十",
        span=TextSpan(start=9, end=13),
        confidence=0.95,
        reason="Weak numeric hypothesis",
        category="percentage",
        sensitive=True,
    )

    result = apply_corrections(raw_transcript, (proposal,), CorrectionPolicy())

    assert result.segments[0].corrected_text == "我们讨论夏普币率和百分之四十的回报。"
    assert result.corrections[0].decision is CorrectionDecision.APPLY_AND_FLAG


def test_low_confidence_proposal_is_retained_and_marked(raw_transcript: RawTranscript) -> None:
    proposal = CorrectionProposal(
        segment_id="seg-1",
        original="夏普币率",
        corrected="夏普比率",
        span=TextSpan(start=4, end=8),
        confidence=0.40,
        reason="Insufficient context",
        category="finance_term",
    )

    result = apply_corrections(raw_transcript, (proposal,), CorrectionPolicy())

    assert result.segments[0].corrected_text == raw_transcript.segments[0].text
    assert result.corrections[0].decision is CorrectionDecision.RETAIN_UNCERTAIN
    assert result.uncertainties[0].text == "夏普币率"


def test_stale_source_span_fails_closed(raw_transcript: RawTranscript) -> None:
    proposal = CorrectionProposal(
        segment_id="seg-1",
        original="不匹配",
        corrected="夏普比率",
        span=TextSpan(start=4, end=8),
        confidence=0.99,
        reason="Fixture",
        category="finance_term",
    )

    with pytest.raises(CorrectionConflictError, match="source mismatch"):
        apply_corrections(raw_transcript, (proposal,), CorrectionPolicy())

