"""Stage-oriented orchestration that retains every completed artifact."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from voicenote import __version__
from voicenote.config import VoiceNoteConfig
from voicenote.core.audio import prepare_audio
from voicenote.core.correction import CorrectionPolicy, apply_corrections
from voicenote.core.extraction import extract_semantic_document
from voicenote.core.notes import create_clean_notes
from voicenote.core.references import ad_hoc_terminology, load_finance_terminology
from voicenote.core.schemas import (
    CleanNotes,
    CorrectedTranscript,
    ExecutiveBrief,
    MeetingMinutes,
    ProcessingStage,
    RunManifest,
    SemanticDocument,
    VoiceNoteResult,
)
from voicenote.exceptions import ProviderNotConfiguredError
from voicenote.providers.base import (
    CorrectionContext,
    CorrectionProvider,
    ReasoningProvider,
    TranscriptionOptions,
    TranscriptionProvider,
)
from voicenote.skills.loader import load_skill

_STAGE_ORDER = {
    ProcessingStage.TRANSCRIPT: 1,
    ProcessingStage.CORRECTED: 2,
    ProcessingStage.NOTES: 3,
    ProcessingStage.MINUTES: 4,
    ProcessingStage.BRIEF: 5,
}


@dataclass(frozen=True, slots=True)
class PipelineProviders:
    transcription: TranscriptionProvider | None = None
    correction: CorrectionProvider | None = None
    reasoning: ReasoningProvider | None = None


class VoiceNotePipeline:
    def __init__(
        self,
        providers: PipelineProviders | None = None,
        config: VoiceNoteConfig | None = None,
    ) -> None:
        self.providers = providers or PipelineProviders()
        self.config = config or VoiceNoteConfig()

    def process(
        self,
        audio_path: Path,
        *,
        until: ProcessingStage = ProcessingStage.CORRECTED,
        language: str | None = None,
        terminology: tuple[str, ...] = (),
        skill: str | None = None,
    ) -> VoiceNoteResult:
        """Run implemented stages and fail explicitly at unfinished provider boundaries."""

        started_at = datetime.now(UTC)
        audio = prepare_audio(audio_path)
        transcription = self.providers.transcription
        if transcription is None:
            raise ProviderNotConfiguredError(
                "Transcription requires an explicitly configured provider; no audio was uploaded"
            )

        raw = transcription.transcribe(audio, TranscriptionOptions(language=language))
        completed: list[ProcessingStage] = [ProcessingStage.TRANSCRIPT]
        corrected: CorrectedTranscript | None = None
        semantic_document: SemanticDocument | None = None
        notes: CleanNotes | None = None
        meeting_minutes: MeetingMinutes | None = None
        executive_brief: ExecutiveBrief | None = None

        if _STAGE_ORDER[until] >= _STAGE_ORDER[ProcessingStage.CORRECTED]:
            correction = self.providers.correction
            if correction is None:
                raise ProviderNotConfiguredError(
                    "Correction requires an explicitly configured provider "
                    "or NoOpCorrectionProvider"
                )
            reference_terms = list(ad_hoc_terminology(terminology))
            if skill == "finance_meeting":
                reference_terms.extend(load_finance_terminology())
            proposals = correction.propose(
                raw,
                CorrectionContext(
                    terminology=tuple(reference_terms),
                    language_hints=(language,) if language else (),
                ),
            )
            corrected = apply_corrections(raw, proposals, self._correction_policy())
            completed.append(ProcessingStage.CORRECTED)

        if _STAGE_ORDER[until] >= _STAGE_ORDER[ProcessingStage.NOTES]:
            reasoning = self.providers.reasoning
            if reasoning is None:
                raise ProviderNotConfiguredError(
                    "Notes require an explicitly configured reasoning provider"
                )
            assert corrected is not None
            semantic_document = extract_semantic_document(corrected, reasoning)
            notes = create_clean_notes(semantic_document, corrected, reasoning)
            completed.append(ProcessingStage.NOTES)

        if _STAGE_ORDER[until] >= _STAGE_ORDER[ProcessingStage.MINUTES]:
            if skill is None:
                raise ProviderNotConfiguredError(
                    "Domain minutes require an explicitly selected skill"
                )
            assert semantic_document is not None
            assert self.providers.reasoning is not None
            domain_skill = load_skill(skill)
            meeting_minutes = domain_skill.organize(
                semantic_document, self.providers.reasoning
            )
            completed.append(ProcessingStage.MINUTES)

            if _STAGE_ORDER[until] >= _STAGE_ORDER[ProcessingStage.BRIEF]:
                executive_brief = domain_skill.create_brief(
                    meeting_minutes, semantic_document, self.providers.reasoning
                )
                completed.append(ProcessingStage.BRIEF)

        provider_names = {"transcription": transcription.name}
        if self.providers.correction is not None:
            provider_names["correction"] = self.providers.correction.name
        if self.providers.reasoning is not None:
            provider_names["reasoning"] = self.providers.reasoning.name

        return VoiceNoteResult(
            manifest=RunManifest(
                voicenote_version=__version__,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                requested_stage=until,
                completed_stages=tuple(completed),
                providers=provider_names,
            ),
            raw_transcript=raw,
            corrected_transcript=corrected,
            semantic_document=semantic_document,
            notes=notes,
            meeting_minutes=meeting_minutes,
            executive_brief=executive_brief,
        )

    def _correction_policy(self) -> CorrectionPolicy:
        return CorrectionPolicy(
            high_threshold=self.config.high_confidence_threshold,
            medium_threshold=self.config.medium_confidence_threshold,
            sensitive_high_threshold=self.config.sensitive_high_threshold,
            sensitive_medium_threshold=self.config.sensitive_medium_threshold,
        )

