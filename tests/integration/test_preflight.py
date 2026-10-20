from pathlib import Path
from unittest.mock import Mock

import pytest

from voicenote.config import VoiceNoteConfig
from voicenote.core.schemas import ProcessingStage, RawTranscript
from voicenote.exceptions import (
    CloudProcessingDisabledError,
    ConfigurationError,
    OptionalDependencyError,
    ProviderNotConfiguredError,
    SkillNotFoundError,
)
from voicenote.pipeline import PipelineProviders, VoiceNotePipeline
from voicenote.providers.base import (
    CorrectionProvider,
    NoOpCorrectionProvider,
    ReasoningProvider,
    TranscriptionProvider,
)
from voicenote.providers.correction import OpenAICorrectionProvider
from voicenote.providers.reasoning import OpenAIReasoningConfig, OpenAIReasoningProvider
from voicenote.providers.transcription import LocalWhisperProvider, OpenAITranscriptionProvider


def test_missing_transcription_fails_before_reading_audio() -> None:
    with pytest.raises(ProviderNotConfiguredError, match="Transcription"):
        VoiceNotePipeline().process(Path("never-read.wav"), until=ProcessingStage.TRANSCRIPT)


@pytest.mark.parametrize(
    ("stage", "skill", "has_correction", "has_reasoning", "error", "message"),
    [
        (ProcessingStage.CORRECTED, None, False, False, ProviderNotConfiguredError, "Correction"),
        (ProcessingStage.NOTES, None, True, False, ProviderNotConfiguredError, "reasoning"),
        (ProcessingStage.MINUTES, None, True, True, ProviderNotConfiguredError, "skill"),
        (ProcessingStage.BRIEF, "typo", True, True, SkillNotFoundError, "typo"),
        (ProcessingStage.TRANSCRIPT, "typo", False, False, SkillNotFoundError, "typo"),
    ],
)
def test_bad_configuration_never_starts_any_provider(
    stage: ProcessingStage,
    skill: str | None,
    has_correction: bool,
    has_reasoning: bool,
    error: type[Exception],
    message: str,
) -> None:
    asr = Mock(spec=TranscriptionProvider)
    correction = Mock(spec=CorrectionProvider) if has_correction else None
    reasoning = Mock(spec=ReasoningProvider) if has_reasoning else None
    pipeline = VoiceNotePipeline(PipelineProviders(asr, correction, reasoning))

    # Even hashing/reading a file must not be necessary to detect configuration errors.
    with pytest.raises(error, match=message):
        pipeline.process(Path("never-read.wav"), until=stage, skill=skill)

    asr.transcribe.assert_not_called()
    if correction is not None:
        correction.propose.assert_not_called()
    if reasoning is not None:
        reasoning.generate_structured.assert_not_called()


@pytest.mark.parametrize("capability", ["transcription", "correction", "reasoning"])
def test_cloud_consent_checked_before_upstream_processing(capability: str) -> None:
    asr = Mock(spec=TranscriptionProvider)
    correction = Mock(spec=CorrectionProvider)
    reasoning = Mock(spec=ReasoningProvider)
    providers = PipelineProviders(
        OpenAITranscriptionProvider() if capability == "transcription" else asr,
        OpenAICorrectionProvider() if capability == "correction" else correction,
        OpenAIReasoningProvider() if capability == "reasoning" else reasoning,
    )
    with pytest.raises(CloudProcessingDisabledError, match=capability):
        VoiceNotePipeline(providers).process(Path("never-read.wav"), until=ProcessingStage.NOTES)
    asr.transcribe.assert_not_called()
    correction.propose.assert_not_called()
    reasoning.generate_structured.assert_not_called()


def test_missing_sdk_fails_before_asr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("voicenote.providers.validation.find_spec", lambda _: None)
    asr = Mock(spec=TranscriptionProvider)
    providers = PipelineProviders(
        asr, NoOpCorrectionProvider(),
        OpenAIReasoningProvider(OpenAIReasoningConfig(allow_cloud_processing=True)),
    )
    with pytest.raises(OptionalDependencyError):
        VoiceNotePipeline(providers).process(Path("never-read.wav"), until=ProcessingStage.NOTES)
    asr.transcribe.assert_not_called()


def test_missing_key_fails_before_asr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("voicenote.providers.validation.find_spec", lambda _: object())
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    asr = Mock(spec=TranscriptionProvider)
    providers = PipelineProviders(
        asr, NoOpCorrectionProvider(),
        OpenAIReasoningProvider(OpenAIReasoningConfig(allow_cloud_processing=True)),
    )
    with pytest.raises(ProviderNotConfiguredError, match="OPENAI_API_KEY"):
        VoiceNotePipeline(providers).process(Path("never-read.wav"), until=ProcessingStage.NOTES)
    asr.transcribe.assert_not_called()


def test_invalid_thresholds_fail_before_asr() -> None:
    asr = Mock(spec=TranscriptionProvider)
    pipeline = VoiceNotePipeline(
        PipelineProviders(asr, NoOpCorrectionProvider()),
        VoiceNoteConfig(medium_confidence_threshold=0.95, high_confidence_threshold=0.9),
    )
    with pytest.raises(ConfigurationError, match="correction policy"):
        pipeline.process(Path("never-read.wav"))
    asr.transcribe.assert_not_called()


def test_unused_cloud_provider_does_not_block_shorter_stage(
    audio_file: Path, raw_transcript: RawTranscript,
) -> None:
    asr = Mock(spec=TranscriptionProvider)
    asr.name = "fixture"
    asr.transcribe.return_value = raw_transcript
    result = VoiceNotePipeline(PipelineProviders(
        asr, reasoning=OpenAIReasoningProvider(),
    )).process(audio_file, until=ProcessingStage.TRANSCRIPT)
    assert result.manifest.completed_stages == (ProcessingStage.TRANSCRIPT,)
    asr.transcribe.assert_called_once()


def test_local_preflight_does_not_load_or_download_model() -> None:
    factory = Mock()
    LocalWhisperProvider(model_factory=factory).validate_configuration()
    factory.assert_not_called()


def test_local_preflight_reports_missing_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "voicenote.providers.transcription.local_whisper.find_spec", lambda _: None
    )
    with pytest.raises(OptionalDependencyError, match="local-asr"):
        LocalWhisperProvider().validate_configuration()


def test_injected_client_does_not_require_environment_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("voicenote.providers.validation.find_spec", lambda _: None)
    client = Mock()
    OpenAIReasoningProvider(
        OpenAIReasoningConfig(allow_cloud_processing=True), client=client
    ).validate_configuration()
    assert not client.mock_calls


def test_missing_skill_references_fail_before_asr(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_references(*_: object) -> tuple[str, ...]:
        raise FileNotFoundError("missing reference")

    monkeypatch.setattr(
        "voicenote.skills.finance_meeting.skill.FinanceMeetingSkill._references", missing_references
    )
    asr = Mock(spec=TranscriptionProvider)
    pipeline = VoiceNotePipeline(PipelineProviders(
        asr, Mock(spec=CorrectionProvider), Mock(spec=ReasoningProvider),
    ))
    with pytest.raises(ConfigurationError, match="reference files"):
        pipeline.process(
            Path("never-read.wav"), until=ProcessingStage.MINUTES, skill="finance_meeting"
        )
    asr.transcribe.assert_not_called()
