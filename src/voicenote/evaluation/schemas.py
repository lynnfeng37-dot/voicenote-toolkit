"""Explicit golden expectations and reports; no model-as-judge dependency."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from voicenote.core.schemas import FrozenModel, TranscriptSegment, VoiceNoteResult


class Artifact(StrEnum):
    RAW = "raw_transcript"
    CORRECTED = "corrected_transcript"
    SEMANTIC = "semantic_document"
    NOTES = "notes"
    MINUTES = "meeting_minutes"
    BRIEF = "executive_brief"


class Dimension(StrEnum):
    NUMERIC = "numeric"
    ENTITY = "entity"
    ATTRIBUTION = "attribution"
    QUALIFICATION = "qualification"
    ACTION = "action"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CONTENT = "content"
    PROVENANCE = "provenance"
    SOURCE_EVIDENCE = "source_evidence"


class FactCheck(FrozenModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    dimension: Dimension
    artifact: Artifact
    source_segment_ids: tuple[str, ...] = Field(min_length=1)
    must_include: tuple[str, ...] = ()
    must_include_any: tuple[str, ...] = ()
    must_exclude: tuple[str, ...] = ()
    expected_speaker: str | None = None

    @field_validator("must_include", "must_include_any", "must_exclude", "source_segment_ids")
    @classmethod
    def reject_blank_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("Check fragments and source IDs must not be blank")
        return values

    @model_validator(mode="after")
    def validate_expectation(self) -> FactCheck:
        if not self.must_include and not self.must_include_any and not self.must_exclude:
            raise ValueError("A check needs at least one required or forbidden fragment")
        if self.expected_speaker is not None:
            if not self.expected_speaker.strip():
                raise ValueError("expected_speaker must not be blank")
            if self.artifact not in {Artifact.RAW, Artifact.CORRECTED, Artifact.SEMANTIC}:
                raise ValueError("This artifact has no structured speaker field")
        return self


class GoldenCase(FrozenModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    description: str
    source_segments: tuple[TranscriptSegment, ...] = Field(min_length=1)
    checks: tuple[FactCheck, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> GoldenCase:
        ids = [segment.id for segment in self.source_segments]
        if any(not source_id.strip() for source_id in ids) or len(ids) != len(set(ids)):
            raise ValueError("Golden source IDs must be non-blank and unique")
        check_ids = [check.id for check in self.checks]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("Golden check IDs must be unique")
        for check in self.checks:
            if not set(check.source_segment_ids) <= set(ids):
                raise ValueError("A golden check cites an unknown source segment")
        return self


class GoldenFixture(FrozenModel):
    case: GoldenCase
    result: VoiceNoteResult


class CheckOutcome(FrozenModel):
    id: str
    dimension: Dimension
    artifact: Artifact
    passed: bool
    reason: str
    observation_paths: tuple[str, ...] = ()


class DimensionScore(FrozenModel):
    passed: int
    total: int
    pass_rate: float


class CaseReport(FrozenModel):
    case_id: str
    passed: bool
    checks: tuple[CheckOutcome, ...]
    scores: dict[str, DimensionScore]


class SuiteReport(FrozenModel):
    passed: bool
    passed_cases: int
    total_cases: int
    cases: tuple[CaseReport, ...]
