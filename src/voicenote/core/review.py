"""Carry correction concerns downstream independently of model-generated warnings."""

from collections.abc import Iterable

from voicenote.core.schemas import (
    CorrectedTranscript,
    CorrectionDecision,
    ReviewConcern,
    SemanticDocument,
    SemanticItem,
)


def collect_review_concerns(transcript: CorrectedTranscript) -> tuple[ReviewConcern, ...]:
    concerns: list[ReviewConcern] = []
    seen: set[tuple[str, int, int]] = set()
    for record in transcript.corrections:
        if record.decision == CorrectionDecision.AUTO_APPLY:
            continue
        concerns.append(ReviewConcern(
            segment_id=record.segment_id,
            original_text=record.original,
            current_text=(
                record.corrected
                if record.decision == CorrectionDecision.APPLY_AND_FLAG
                else record.original
            ),
            proposed_text=record.corrected,
            original_span=record.span,
            confidence=record.confidence,
            reason=record.reason,
            decision=record.decision,
            category=record.category,
            sensitive=record.sensitive,
            evidence=record.evidence,
        ))
        seen.add((record.segment_id, record.span.start, record.span.end))
    # Accommodate imported transcripts whose uncertainties have no correction records.
    for uncertainty in transcript.uncertainties:
        key = (uncertainty.segment_id, uncertainty.span.start, uncertainty.span.end)
        if key in seen:
            continue
        concerns.append(ReviewConcern(
            segment_id=uncertainty.segment_id,
            original_text=uncertainty.text,
            current_text=uncertainty.text,
            original_span=uncertainty.span,
            confidence=uncertainty.confidence,
            reason=uncertainty.reason,
            decision=CorrectionDecision.RETAIN_UNCERTAIN,
        ))
        seen.add(key)
    return tuple(concerns)


def concerns_for_sources(
    concerns: tuple[ReviewConcern, ...], source_ids: Iterable[str]
) -> tuple[ReviewConcern, ...]:
    sources = set(source_ids)
    return tuple(concern for concern in concerns if concern.segment_id in sources)


def with_semantic_review(
    document: SemanticDocument, transcript: CorrectedTranscript
) -> SemanticDocument:
    concerns = collect_review_concerns(transcript)

    def annotate(items: tuple[SemanticItem, ...]) -> tuple[SemanticItem, ...]:
        return tuple(item.model_copy(update={
            "review_concerns": concerns_for_sources(concerns, item.source_segment_ids)
        }) for item in items)

    return document.model_copy(update={
        "items": annotate(document.items),
        "entities": annotate(document.entities),
        "open_questions": annotate(document.open_questions),
        "review_concerns": concerns,
    })
