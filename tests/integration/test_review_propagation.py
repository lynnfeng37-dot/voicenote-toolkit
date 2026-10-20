import json
from pathlib import Path
from typing import TypeVar

import pytest
from pydantic import BaseModel

from voicenote.artifacts import persist_result
from voicenote.core.correction import CorrectionPolicy, apply_corrections
from voicenote.core.extraction import extract_semantic_document
from voicenote.core.notes import create_clean_notes
from voicenote.core.schemas import (
    AudioSource,
    CorrectionDecision,
    CorrectionProposal,
    ProcessingStage,
    RawTranscript,
    TextSpan,
    TranscriptSegment,
    VoiceNoteResult,
)
from voicenote.pipeline import PipelineProviders, VoiceNotePipeline
from voicenote.providers.base import (
    CorrectionContext,
    CorrectionProvider,
    ReasoningProvider,
    ReasoningRequest,
    TranscriptionOptions,
    TranscriptionProvider,
)

T = TypeVar("T", bound=BaseModel)
SOURCE_TEXT = "Sharp ratio; return 15%; issuer Acme."


def proposals() -> tuple[CorrectionProposal, ...]:
    return tuple(CorrectionProposal(
        segment_id="seg-1", original=original, corrected=corrected,
        span=TextSpan(
            start=SOURCE_TEXT.index(original), end=SOURCE_TEXT.index(original) + len(original)
        ),
        confidence=confidence, reason="Synthetic review example", category=category,
        sensitive=sensitive,
    ) for original, corrected, confidence, category, sensitive in (
        ("Sharp", "Sharpe", 0.99, "term", False),
        ("15%", "50%", 0.80, "percentage", True),
        ("Acme", "ACME", 0.95, "company_name", True),
    ))


class ScriptedASR(TranscriptionProvider):
    name = "scripted-asr"

    def __init__(self, raw: RawTranscript) -> None:
        self.raw = raw

    def transcribe(self, audio: AudioSource, options: TranscriptionOptions) -> RawTranscript:
        del options
        return self.raw.model_copy(update={"audio": audio})


class ScriptedCorrection(CorrectionProvider):
    name = "scripted-correction"

    def propose(
        self, transcript: RawTranscript, context: CorrectionContext
    ) -> tuple[CorrectionProposal, ...]:
        del transcript, context
        return proposals()


class ScriptedReasoning(ReasoningProvider):
    """Return text with no model-authored warnings or review metadata at all."""

    name = "scripted-reasoning"

    def __init__(self, omit_flagged_segment: bool = False) -> None:
        self.requests: list[ReasoningRequest] = []
        self.omit_flagged_segment = omit_flagged_segment

    def generate_structured(self, request: ReasoningRequest, response_model: type[T]) -> T:
        self.requests.append(request)
        if request.task == "extract_semantic_document":
            ids = [segment["id"] for segment in request.payload["segments"]]
            return response_model.model_validate({
                "meeting_type": "internal_investment",
                "items": [{
                    "field": "financial_metric", "content": "Return was 15%; issuer ACME.",
                    "source_segment_ids": [source], "speaker": None, "confidence": 0.99,
                } for source in ids if not (self.omit_flagged_segment and source == "seg-1")],
                "entities": [], "open_questions": [],
            })
        section = {
            "title": "Performance", "paragraphs": [], "bullets": ["Return was 15%; issuer ACME."],
            "source_segment_ids": ["seg-1"],
        }
        if request.task == "create_clean_notes":
            sections = [section] if not self.omit_flagged_segment else []
            return response_model.model_validate({"title": "Notes", "sections": sections})
        if request.task == "create_finance_meeting_minutes":
            return response_model.model_validate({
                "meeting_type": "internal_investment", "title": "Minutes",
                "sections": [section], "warnings": [],
            })
        if request.task == "create_finance_executive_brief":
            return response_model.model_validate({
                "what_happened": [], "important_views": [], "changes": [], "decisions": [],
                "risks": [{
                    "text": "Return was 15%; issuer ACME.", "source_segment_ids": ["seg-1"]
                }],
                "actions": [{"text": "Follow-up discussion", "source_segment_ids": ["seg-2"]}],
            })
        raise AssertionError(f"Unexpected task: {request.task}")


@pytest.fixture
def review_transcript(raw_transcript: RawTranscript) -> RawTranscript:
    return raw_transcript.model_copy(update={"segments": (
        TranscriptSegment(id="seg-1", text=SOURCE_TEXT),
        TranscriptSegment(id="seg-2", text="Follow-up discussion."),
    )})


def test_every_stage_receives_and_retains_review_concerns(
    review_transcript: RawTranscript, audio_file: Path, tmp_path: Path,
) -> None:
    reasoning = ScriptedReasoning()
    result = VoiceNotePipeline(PipelineProviders(
        ScriptedASR(review_transcript), ScriptedCorrection(), reasoning,
    )).process(audio_file, until=ProcessingStage.BRIEF, skill="finance_meeting")
    assert result.corrected_transcript is not None
    assert result.semantic_document is not None
    assert result.notes is not None
    assert result.meeting_minutes is not None
    assert result.executive_brief is not None
    assert result.raw_transcript is not None
    assert result.raw_transcript.text == review_transcript.text
    assert "15%" in result.corrected_transcript.text
    assert "50%" not in result.corrected_transcript.text
    assert "Sharpe" in result.corrected_transcript.text

    concerns = result.semantic_document.review_concerns
    assert len(concerns) == 2
    assert concerns[0].decision == CorrectionDecision.RETAIN_UNCERTAIN
    assert concerns[1].decision == CorrectionDecision.APPLY_AND_FLAG
    # Earlier length-changing edits must not re-anchor the stored raw span.
    assert concerns[0].original_span.start == SOURCE_TEXT.index("15%")
    assert concerns[0].original_span.start != result.corrected_transcript.text.index("15%")
    assert result.semantic_document.items[0].review_concerns == concerns
    assert result.semantic_document.items[1].review_concerns == ()
    assert result.notes.review_concerns == concerns
    assert result.notes.sections[0].review_concerns == concerns
    assert result.meeting_minutes.review_concerns == concerns
    assert result.meeting_minutes.sections[0].review_concerns == concerns
    assert result.executive_brief.review_concerns == concerns
    assert result.executive_brief.risks[0].review_concerns == concerns
    assert result.executive_brief.actions[0].review_concerns == ()
    assert "2 correction concern" in result.manifest.warnings[0]

    for request in reasoning.requests:
        payload = request.payload
        if request.task == "create_finance_executive_brief":
            payload = payload["semantic_document"]
        assert len(payload["review_concerns"]) == 2

    run_dir = persist_result(result, tmp_path)
    for filename in ("notes.md", "meeting_minutes.md", "executive_brief.md", "result.md"):
        markdown = (run_dir / filename).read_text(encoding="utf-8")
        assert "requiring review" in markdown
        assert "Original retained" in markdown
        assert "Correction applied but requires review" in markdown
        assert "**15%**" in markdown
    saved = VoiceNoteResult.model_validate_json(
        (run_dir / "result.json").read_text(encoding="utf-8")
    )
    assert saved.executive_brief is not None
    assert saved.executive_brief.review_concerns == concerns
    brief_data = json.loads((run_dir / "executive_brief.json").read_text(encoding="utf-8"))
    assert brief_data["review_concerns"][0]["proposed_text"] == "50%"


def test_extraction_batches_only_receive_their_own_concerns(
    review_transcript: RawTranscript,
) -> None:
    corrected = apply_corrections(review_transcript, proposals(), CorrectionPolicy())
    provider = ScriptedReasoning()
    document = extract_semantic_document(corrected, provider, max_batch_characters=1)
    assert len(provider.requests) == 2
    assert len(provider.requests[0].payload["review_concerns"]) == 2
    assert provider.requests[1].payload["review_concerns"] == []
    assert document.items[0].review_concerns
    assert not document.items[1].review_concerns


def test_omitted_uncertain_content_still_has_document_review_metadata(
    review_transcript: RawTranscript,
) -> None:
    corrected = apply_corrections(review_transcript, proposals(), CorrectionPolicy())
    provider = ScriptedReasoning(omit_flagged_segment=True)
    document = extract_semantic_document(corrected, provider)
    notes = create_clean_notes(document, corrected, provider)
    assert all(item.source_segment_ids == ("seg-2",) for item in document.items)
    assert len(document.review_concerns) == 2
    assert notes.sections == ()
    assert len(notes.review_concerns) == 2
