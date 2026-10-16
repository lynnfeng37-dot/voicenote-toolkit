"""Build and validate source-grounded semantic documents."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from voicenote.core.schemas import (
    CorrectedSegment,
    CorrectedTranscript,
    SemanticDocument,
    SemanticItem,
)
from voicenote.exceptions import ProvenanceError
from voicenote.providers.base import ReasoningProvider, ReasoningRequest


class ExtractedSemanticItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    content: str
    source_segment_ids: list[str]
    speaker: str | None
    confidence: float = Field(ge=0, le=1)


class ExtractedSemanticDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meeting_type: str | None
    items: list[ExtractedSemanticItem]
    entities: list[ExtractedSemanticItem]
    open_questions: list[ExtractedSemanticItem]


def extract_semantic_document(
    transcript: CorrectedTranscript,
    provider: ReasoningProvider,
    *,
    max_batch_characters: int = 12_000,
) -> SemanticDocument:
    """Extract semantic items in bounded batches, rejecting invented citations."""
    if max_batch_characters <= 0:
        raise ValueError("max_batch_characters must be positive")
    extracted: list[ExtractedSemanticDocument] = []
    for batch in _batch_segments(transcript.segments, max_batch_characters):
        result = provider.generate_structured(
            build_extraction_request(batch), ExtractedSemanticDocument
        )
        _validate_batch_sources(result, {segment.id for segment in batch})
        extracted.append(result)
    meeting_types = {item.meeting_type for item in extracted if item.meeting_type}
    document = SemanticDocument(
        meeting_type=next(iter(meeting_types)) if len(meeting_types) == 1 else None,
        items=tuple(_convert(item) for batch in extracted for item in batch.items),
        entities=tuple(_convert(item) for batch in extracted for item in batch.entities),
        open_questions=tuple(
            _convert(item) for batch in extracted for item in batch.open_questions
        ),
    )
    from voicenote.core.validation import validate_semantic_document
    validate_semantic_document(document, transcript)
    return document


def build_extraction_request(segments: tuple[CorrectedSegment, ...]) -> ReasoningRequest:
    """Create a provider-neutral request containing only corrected, citable segments."""
    return ReasoningRequest(
        task="extract_semantic_document",
        instructions=(
            "Extract only claims explicitly supported by the supplied corrected segments. "
            "Preserve names, numbers, units, dates, qualifications, uncertainty, and speaker "
            "attribution. Do not infer missing facts. Every item, entity, and open question must "
            "cite one or more supplied segment IDs."
        ),
        payload={"segments": [
            {
                "id": segment.id, "text": segment.corrected_text,
                "speaker": segment.speaker, "language": segment.language,
                "start_seconds": segment.start_seconds, "end_seconds": segment.end_seconds,
            }
            for segment in segments
        ]},
    )


def _batch_segments(
    segments: tuple[CorrectedSegment, ...], limit: int
) -> tuple[tuple[CorrectedSegment, ...], ...]:
    batches: list[tuple[CorrectedSegment, ...]] = []
    current: list[CorrectedSegment] = []
    size = 0
    for segment in segments:
        segment_size = len(segment.corrected_text)
        if current and size + segment_size > limit:
            batches.append(tuple(current))
            current, size = [], 0
        current.append(segment)
        size += segment_size
    if current:
        batches.append(tuple(current))
    return tuple(batches)


def _validate_batch_sources(document: ExtractedSemanticDocument, allowed: set[str]) -> None:
    for item in (*document.items, *document.entities, *document.open_questions):
        if not item.source_segment_ids:
            raise ProvenanceError("Every semantic item must cite at least one source segment")
        unknown = set(item.source_segment_ids) - allowed
        if unknown:
            raise ProvenanceError(
                f"Semantic item cites unavailable batch segments: {sorted(unknown)}"
            )


def _convert(item: ExtractedSemanticItem) -> SemanticItem:
    return SemanticItem(
        field=item.field, content=item.content,
        source_segment_ids=tuple(item.source_segment_ids),
        speaker=item.speaker, confidence=item.confidence,
    )
