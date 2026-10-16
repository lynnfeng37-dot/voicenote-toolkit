"""Create adaptive clean notes from the source-grounded semantic IR."""

from pydantic import BaseModel, ConfigDict

from voicenote.core.schemas import CleanNotes, CorrectedTranscript, NoteSection, SemanticDocument
from voicenote.core.validation import validate_clean_notes
from voicenote.providers.base import ReasoningProvider, ReasoningRequest


class GeneratedNoteSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None
    paragraphs: list[str]
    bullets: list[str]
    source_segment_ids: list[str]


class GeneratedCleanNotes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None
    sections: list[GeneratedNoteSection]


def create_clean_notes(
    document: SemanticDocument, transcript: CorrectedTranscript, provider: ReasoningProvider
) -> CleanNotes:
    generated = provider.generate_structured(build_notes_request(document), GeneratedCleanNotes)
    notes = CleanNotes(
        title=generated.title,
        sections=tuple(NoteSection(
            title=section.title, paragraphs=tuple(section.paragraphs),
            bullets=tuple(section.bullets),
            source_segment_ids=tuple(section.source_segment_ids),
        ) for section in generated.sections),
    )
    validate_clean_notes(notes, document, transcript)
    return notes


def build_notes_request(document: SemanticDocument) -> ReasoningRequest:
    return ReasoningRequest(
        task="create_clean_notes",
        instructions=(
            "Organize concise, readable notes using only the supplied semantic document. Adapt "
            "the section structure to the content; remove filler and repetition, but preserve "
            "important details and qualifications. Never add facts or strengthen claims. Every "
            "non-empty section must cite source segment IDs already present in its semantic items."
        ),
        payload=document.model_dump(mode="json"),
    )
