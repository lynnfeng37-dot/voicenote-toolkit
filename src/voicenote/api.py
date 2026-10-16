"""Small user-facing facade over the stage pipeline."""

from __future__ import annotations

from pathlib import Path

from voicenote.config import VoiceNoteConfig
from voicenote.core.schemas import ProcessingStage, VoiceNoteResult
from voicenote.pipeline import PipelineProviders, VoiceNotePipeline
from voicenote.providers.factory import (
    build_correction_provider,
    build_reasoning_provider,
    build_transcription_provider,
)


class VoiceNote:
    def __init__(
        self,
        audio: str | Path,
        *,
        providers: PipelineProviders | None = None,
        config: VoiceNoteConfig | None = None,
    ) -> None:
        self.audio = Path(audio)
        effective_config = config or VoiceNoteConfig()
        effective_providers = providers
        if effective_providers is None and effective_config.transcription_provider is not None:
            effective_providers = PipelineProviders(
                transcription=build_transcription_provider(effective_config),
                correction=(
                    build_correction_provider(effective_config)
                    if effective_config.correction_provider is not None
                    else None
                ),
                reasoning=(
                    build_reasoning_provider(effective_config)
                    if effective_config.reasoning_provider is not None
                    else None
                ),
            )
        self.pipeline = VoiceNotePipeline(providers=effective_providers, config=effective_config)

    def process(
        self,
        *,
        until: ProcessingStage | str = ProcessingStage.CORRECTED,
        language: str | None = None,
        terminology: tuple[str, ...] = (),
        skill: str | None = None,
    ) -> VoiceNoteResult:
        target = until if isinstance(until, ProcessingStage) else ProcessingStage(until)
        return self.pipeline.process(
            self.audio,
            until=target,
            language=language,
            terminology=terminology,
            skill=skill,
        )

