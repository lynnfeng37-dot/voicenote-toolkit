"""Deterministic provenance validation for generated artifacts."""

from voicenote.core.schemas import CleanNotes, CorrectedTranscript, SemanticDocument
from voicenote.exceptions import ProvenanceError


def validate_semantic_document(document: SemanticDocument, transcript: CorrectedTranscript) -> None:
    known = {segment.id for segment in transcript.segments}
    for item in (*document.items, *document.entities, *document.open_questions):
        if not item.source_segment_ids:
            raise ProvenanceError("Every semantic item must cite at least one source segment")
        unknown = set(item.source_segment_ids) - known
        if unknown:
            raise ProvenanceError(f"Unknown semantic source segments: {sorted(unknown)}")


def validate_clean_notes(
    notes: CleanNotes, document: SemanticDocument, transcript: CorrectedTranscript
) -> None:
    known = {segment.id for segment in transcript.segments}
    supported = {
        source_id
        for item in (*document.items, *document.entities, *document.open_questions)
        for source_id in item.source_segment_ids
    }
    for section in notes.sections:
        if not section.paragraphs and not section.bullets:
            continue
        if not section.source_segment_ids:
            raise ProvenanceError("Every non-empty note section must cite source segments")
        unknown = set(section.source_segment_ids) - known
        unsupported = set(section.source_segment_ids) - supported
        if unknown:
            raise ProvenanceError(f"Unknown note source segments: {sorted(unknown)}")
        if unsupported:
            raise ProvenanceError(
                f"Note citations are absent from semantic IR: {sorted(unsupported)}"
            )
