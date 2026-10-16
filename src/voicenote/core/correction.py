"""Deterministic correction policy and conflict-safe text application."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field, model_validator

from voicenote.core.schemas import (
    CorrectedSegment,
    CorrectedTranscript,
    CorrectionDecision,
    CorrectionProposal,
    CorrectionRecord,
    RawTranscript,
    UncertainSpan,
)
from voicenote.exceptions import CorrectionConflictError


class CorrectionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    high_threshold: float = Field(default=0.90, ge=0, le=1)
    medium_threshold: float = Field(default=0.70, ge=0, le=1)
    sensitive_high_threshold: float = Field(default=0.98, ge=0, le=1)
    sensitive_medium_threshold: float = Field(default=0.92, ge=0, le=1)

    @model_validator(mode="after")
    def validate_thresholds(self) -> CorrectionPolicy:
        if self.medium_threshold > self.high_threshold:
            raise ValueError("medium_threshold must not exceed high_threshold")
        if self.sensitive_medium_threshold > self.sensitive_high_threshold:
            raise ValueError("sensitive_medium_threshold must not exceed sensitive_high_threshold")
        return self

    def decide(self, proposal: CorrectionProposal) -> CorrectionDecision:
        high = self.sensitive_high_threshold if proposal.sensitive else self.high_threshold
        medium = self.sensitive_medium_threshold if proposal.sensitive else self.medium_threshold
        if proposal.confidence >= high:
            return CorrectionDecision.AUTO_APPLY
        if proposal.confidence >= medium:
            return CorrectionDecision.APPLY_AND_FLAG
        return CorrectionDecision.RETAIN_UNCERTAIN


def apply_corrections(
    transcript: RawTranscript,
    proposals: tuple[CorrectionProposal, ...],
    policy: CorrectionPolicy,
) -> CorrectedTranscript:
    """Apply non-overlapping proposals while preserving the immutable raw transcript."""

    proposals_by_segment: dict[str, list[CorrectionProposal]] = defaultdict(list)
    for proposal in proposals:
        proposals_by_segment[proposal.segment_id].append(proposal)

    known_ids = {segment.id for segment in transcript.segments}
    unknown_ids = set(proposals_by_segment) - known_ids
    if unknown_ids:
        raise CorrectionConflictError(f"Unknown segment ids: {sorted(unknown_ids)}")

    corrected_segments: list[CorrectedSegment] = []
    records: list[CorrectionRecord] = []
    uncertainties: list[UncertainSpan] = []

    for segment in transcript.segments:
        text = segment.text
        segment_proposals = sorted(
            proposals_by_segment.get(segment.id, []), key=lambda item: item.span.start
        )
        _validate_proposals(text, segment_proposals)

        for proposal in reversed(segment_proposals):
            decision = policy.decide(proposal)
            records.append(
                CorrectionRecord(
                    **proposal.model_dump(),
                    decision=decision,
                )
            )
            if decision is CorrectionDecision.RETAIN_UNCERTAIN:
                uncertainties.append(
                    UncertainSpan(
                        segment_id=segment.id,
                        text=proposal.original,
                        span=proposal.span,
                        reason=proposal.reason,
                        confidence=proposal.confidence,
                    )
                )
                continue
            text = text[: proposal.span.start] + proposal.corrected + text[proposal.span.end :]

        corrected_segments.append(
            CorrectedSegment(
                id=segment.id,
                original_text=segment.text,
                corrected_text=text,
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                speaker=segment.speaker,
                language=segment.language,
            )
        )

    return CorrectedTranscript(
        raw_transcript=transcript,
        segments=tuple(corrected_segments),
        corrections=tuple(sorted(records, key=lambda item: (item.segment_id, item.span.start))),
        uncertainties=tuple(
            sorted(uncertainties, key=lambda item: (item.segment_id, item.span.start))
        ),
    )


def _validate_proposals(text: str, proposals: list[CorrectionProposal]) -> None:
    previous_end = 0
    for proposal in proposals:
        if proposal.span.start < previous_end:
            raise CorrectionConflictError("Overlapping correction proposals are not allowed")
        if proposal.span.end > len(text):
            raise CorrectionConflictError("Correction span exceeds the segment length")
        actual = text[proposal.span.start : proposal.span.end]
        if actual != proposal.original:
            raise CorrectionConflictError(
                f"Correction source mismatch: expected {proposal.original!r}, found {actual!r}"
            )
        previous_end = proposal.span.end

