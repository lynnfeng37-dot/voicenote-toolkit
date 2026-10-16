from typing import TypeVar, cast

import pytest
from pydantic import BaseModel

from voicenote.core.correction import CorrectionPolicy, apply_corrections
from voicenote.core.extraction import (
    ExtractedSemanticDocument,
    ExtractedSemanticItem,
    extract_semantic_document,
)
from voicenote.core.notes import GeneratedCleanNotes, GeneratedNoteSection, create_clean_notes
from voicenote.core.schemas import RawTranscript
from voicenote.exceptions import ProvenanceError
from voicenote.providers.base import ReasoningProvider, ReasoningRequest

T = TypeVar("T", bound=BaseModel)


class FixtureReasoning(ReasoningProvider):
    name = "fixture"

    def __init__(self, bad_source: bool = False) -> None:
        self.bad_source = bad_source

    def generate_structured(self, request: ReasoningRequest, response_model: type[T]) -> T:
        if request.task == "extract_semantic_document":
            source = "missing" if self.bad_source else request.payload["segments"][0]["id"]
            value = ExtractedSemanticDocument(
                meeting_type="investment",
                items=[ExtractedSemanticItem(
                    field="view", content="预期回报为百分之十", source_segment_ids=[source],
                    speaker="S1", confidence=0.9,
                )], entities=[], open_questions=[],
            )
        else:
            value = GeneratedCleanNotes(
                title="投资讨论",
                sections=[GeneratedNoteSection(
                    title="核心观点", paragraphs=[], bullets=["预期回报为百分之十"],
                    source_segment_ids=["seg-1"],
                )],
            )
        return cast(T, value)


def test_extract_then_create_notes_keeps_provenance(raw_transcript: RawTranscript) -> None:
    corrected = apply_corrections(raw_transcript, (), CorrectionPolicy())
    provider = FixtureReasoning()
    document = extract_semantic_document(corrected, provider)
    notes = create_clean_notes(document, corrected, provider)
    assert document.items[0].source_segment_ids == ("seg-1",)
    assert notes.sections[0].source_segment_ids == ("seg-1",)


def test_extraction_rejects_unknown_batch_source(raw_transcript: RawTranscript) -> None:
    corrected = apply_corrections(raw_transcript, (), CorrectionPolicy())
    with pytest.raises(ProvenanceError, match="unavailable batch"):
        extract_semantic_document(corrected, FixtureReasoning(bad_source=True))
