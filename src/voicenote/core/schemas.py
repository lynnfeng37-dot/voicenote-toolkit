"""Stable intermediate representations shared by the pipeline and extensions."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    """Immutable base used for evidence-bearing artifacts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ProcessingStage(StrEnum):
    TRANSCRIPT = "transcript"
    CORRECTED = "corrected"
    NOTES = "notes"
    MINUTES = "minutes"
    BRIEF = "brief"


class CorrectionDecision(StrEnum):
    AUTO_APPLY = "auto_apply"
    APPLY_AND_FLAG = "apply_and_flag"
    RETAIN_UNCERTAIN = "retain_uncertain"


class TextSpan(FrozenModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> TextSpan:
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class AudioSource(FrozenModel):
    path: str
    media_type: str | None = None
    sha256: str
    size_bytes: int = Field(ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)


class TranscriptSegment(FrozenModel):
    id: str
    text: str
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    speaker: str | None = None
    language: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timestamps(self) -> TranscriptSegment:
        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds < self.start_seconds
        ):
            raise ValueError("end_seconds must not precede start_seconds")
        return self


class ProviderMetadata(FrozenModel):
    provider: str
    model: str | None = None
    request_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class RawTranscript(FrozenModel):
    """Immutable ASR output. No downstream stage may rewrite this object."""

    audio: AudioSource
    segments: tuple[TranscriptSegment, ...]
    provider: ProviderMetadata
    detected_languages: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        return "\n".join(segment.text for segment in self.segments)


class TerminologyEntry(FrozenModel):
    canonical: str
    variants: tuple[str, ...] = ()
    category: str = "term"
    sensitive: bool = False
    notes: str | None = None


class CorrectionProposal(FrozenModel):
    segment_id: str
    original: str
    corrected: str
    span: TextSpan
    confidence: float = Field(ge=0, le=1)
    reason: str
    category: str
    evidence: tuple[str, ...] = ()
    sensitive: bool = False


class CorrectionRecord(FrozenModel):
    segment_id: str
    original: str
    corrected: str
    span: TextSpan
    confidence: float = Field(ge=0, le=1)
    decision: CorrectionDecision
    reason: str
    category: str
    evidence: tuple[str, ...] = ()
    sensitive: bool = False


class UncertainSpan(FrozenModel):
    segment_id: str
    text: str
    span: TextSpan
    reason: str
    confidence: float = Field(ge=0, le=1)


class CorrectedSegment(FrozenModel):
    id: str
    original_text: str
    corrected_text: str
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    speaker: str | None = None
    language: str | None = None


class CorrectedTranscript(FrozenModel):
    raw_transcript: RawTranscript
    segments: tuple[CorrectedSegment, ...]
    corrections: tuple[CorrectionRecord, ...] = ()
    uncertainties: tuple[UncertainSpan, ...] = ()

    @property
    def text(self) -> str:
        return "\n".join(segment.corrected_text for segment in self.segments)


class SemanticItem(FrozenModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    field: str
    content: str
    source_segment_ids: tuple[str, ...] = ()
    speaker: str | None = None
    confidence: float = Field(ge=0, le=1)
    attributes: dict[str, Any] = Field(default_factory=dict)


class SemanticDocument(FrozenModel):
    meeting_type: str | None = None
    items: tuple[SemanticItem, ...]
    entities: tuple[SemanticItem, ...] = ()
    open_questions: tuple[SemanticItem, ...] = ()


class NoteSection(FrozenModel):
    title: str | None = None
    paragraphs: tuple[str, ...] = ()
    bullets: tuple[str, ...] = ()
    source_segment_ids: tuple[str, ...] = ()


class CleanNotes(FrozenModel):
    title: str | None = None
    sections: tuple[NoteSection, ...]


class MeetingMinutes(FrozenModel):
    skill: str
    meeting_type: str
    title: str | None = None
    sections: tuple[NoteSection, ...]
    warnings: tuple[str, ...] = ()


class BriefItem(FrozenModel):
    text: str
    source_segment_ids: tuple[str, ...]


class ExecutiveBrief(FrozenModel):
    what_happened: tuple[BriefItem, ...] = ()
    important_views: tuple[BriefItem, ...] = ()
    changes: tuple[BriefItem, ...] = ()
    decisions: tuple[BriefItem, ...] = ()
    risks: tuple[BriefItem, ...] = ()
    actions: tuple[BriefItem, ...] = ()


class RunManifest(FrozenModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    voicenote_version: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    requested_stage: ProcessingStage
    completed_stages: tuple[ProcessingStage, ...] = ()
    providers: dict[str, str] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()


class VoiceNoteResult(FrozenModel):
    manifest: RunManifest
    raw_transcript: RawTranscript | None = None
    corrected_transcript: CorrectedTranscript | None = None
    semantic_document: SemanticDocument | None = None
    notes: CleanNotes | None = None
    meeting_minutes: MeetingMinutes | None = None
    executive_brief: ExecutiveBrief | None = None

