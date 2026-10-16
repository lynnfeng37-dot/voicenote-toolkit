from __future__ import annotations

from pathlib import Path
from typing import TypeVar, cast

from pydantic import BaseModel

from voicenote.core.extraction import ExtractedSemanticDocument, ExtractedSemanticItem
from voicenote.core.notes import GeneratedCleanNotes, GeneratedNoteSection
from voicenote.core.schemas import (
    AudioSource,
    CorrectionProposal,
    ProcessingStage,
    ProviderMetadata,
    RawTranscript,
    TextSpan,
    TranscriptSegment,
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
from voicenote.skills.finance_meeting.skill import (
    GeneratedBriefItem,
    GeneratedExecutiveBrief,
    GeneratedFinanceMinutes,
    GeneratedMinutesSection,
)

T = TypeVar("T", bound=BaseModel)


class FixtureTranscriptionProvider(TranscriptionProvider):
    name = "fixture-asr"

    def transcribe(self, audio: AudioSource, options: TranscriptionOptions) -> RawTranscript:
        del options
        return RawTranscript(
            audio=audio,
            segments=(TranscriptSegment(id="seg-1", text="夏普币率"),),
            provider=ProviderMetadata(provider=self.name),
        )


class FixtureCorrectionProvider(CorrectionProvider):
    name = "fixture-correction"

    def propose(
        self, transcript: RawTranscript, context: CorrectionContext
    ) -> tuple[CorrectionProposal, ...]:
        del transcript, context
        return (
            CorrectionProposal(
                segment_id="seg-1",
                original="夏普币率",
                corrected="夏普比率",
                span=TextSpan(start=0, end=4),
                confidence=0.99,
                reason="Fixture terminology",
                category="finance_term",
            ),
        )


class CapturingCorrectionProvider(CorrectionProvider):
    name = "capture"

    def __init__(self) -> None:
        self.context: CorrectionContext | None = None

    def propose(
        self, transcript: RawTranscript, context: CorrectionContext
    ) -> tuple[CorrectionProposal, ...]:
        del transcript
        self.context = context
        return ()


class FixtureReasoningProvider(ReasoningProvider):
    name = "fixture-reasoning"

    def generate_structured(self, request: ReasoningRequest, response_model: type[T]) -> T:
        del response_model
        if request.task == "extract_semantic_document":
            result = ExtractedSemanticDocument(
                meeting_type="investment",
                items=[ExtractedSemanticItem(
                    field="metric", content="夏普比率", source_segment_ids=["seg-1"],
                    speaker=None, confidence=0.99,
                )], entities=[], open_questions=[],
            )
        elif request.task == "create_clean_notes":
            result = GeneratedCleanNotes(
                title="讨论笔记",
                sections=[GeneratedNoteSection(
                    title="指标", paragraphs=[], bullets=["夏普比率"],
                    source_segment_ids=["seg-1"],
                )],
            )
        elif request.task == "create_finance_meeting_minutes":
            result = GeneratedFinanceMinutes(
                meeting_type="internal_investment", title="投资会议",
                sections=[GeneratedMinutesSection(
                    title="核心观点", paragraphs=[], bullets=["夏普比率"],
                    source_segment_ids=["seg-1"],
                )], warnings=[],
            )
        else:
            result = GeneratedExecutiveBrief(
                what_happened=[],
                important_views=[GeneratedBriefItem(
                    text="关注夏普比率", source_segment_ids=["seg-1"],
                )],
                changes=[], decisions=[], risks=[], actions=[],
            )
        return cast(T, result)


def test_pipeline_retains_raw_and_corrected_artifacts(audio_file: Path) -> None:
    pipeline = VoiceNotePipeline(
        providers=PipelineProviders(
            transcription=FixtureTranscriptionProvider(),
            correction=FixtureCorrectionProvider(),
        )
    )

    result = pipeline.process(audio_file, until=ProcessingStage.CORRECTED)

    assert result.raw_transcript is not None
    assert result.corrected_transcript is not None
    assert result.raw_transcript.text == "夏普币率"
    assert result.corrected_transcript.text == "夏普比率"
    assert result.manifest.completed_stages == (
        ProcessingStage.TRANSCRIPT,
        ProcessingStage.CORRECTED,
    )


def test_finance_skill_adds_reference_terminology(audio_file: Path) -> None:
    correction = CapturingCorrectionProvider()
    pipeline = VoiceNotePipeline(
        providers=PipelineProviders(
            transcription=FixtureTranscriptionProvider(),
            correction=correction,
        )
    )

    pipeline.process(
        audio_file,
        until=ProcessingStage.CORRECTED,
        skill="finance_meeting",
        terminology=("自定义术语",),
    )

    assert correction.context is not None
    canonical_terms = {entry.canonical for entry in correction.context.terminology}
    assert "夏普比率" in canonical_terms
    assert "自定义术语" in canonical_terms


def test_pipeline_generates_source_linked_notes(audio_file: Path) -> None:
    pipeline = VoiceNotePipeline(providers=PipelineProviders(
        transcription=FixtureTranscriptionProvider(),
        correction=FixtureCorrectionProvider(),
        reasoning=FixtureReasoningProvider(),
    ))
    result = pipeline.process(audio_file, until=ProcessingStage.NOTES)
    assert result.semantic_document is not None
    assert result.notes is not None
    assert result.notes.sections[0].source_segment_ids == ("seg-1",)
    assert result.manifest.completed_stages[-1] == ProcessingStage.NOTES


def test_pipeline_generates_finance_minutes_and_brief(audio_file: Path) -> None:
    pipeline = VoiceNotePipeline(providers=PipelineProviders(
        transcription=FixtureTranscriptionProvider(),
        correction=FixtureCorrectionProvider(),
        reasoning=FixtureReasoningProvider(),
    ))
    result = pipeline.process(
        audio_file, until=ProcessingStage.BRIEF, skill="finance_meeting"
    )
    assert result.meeting_minutes is not None
    assert result.executive_brief is not None
    assert result.executive_brief.important_views[0].source_segment_ids == ("seg-1",)
    assert result.manifest.completed_stages == tuple(ProcessingStage)

