"""Construct built-in providers only after an explicit configuration choice."""

from voicenote.config import VoiceNoteConfig
from voicenote.exceptions import ProviderNotConfiguredError
from voicenote.providers.base import (
    CorrectionProvider,
    NoOpCorrectionProvider,
    ReasoningProvider,
    TranscriptionProvider,
)
from voicenote.providers.correction import OpenAICorrectionConfig, OpenAICorrectionProvider
from voicenote.providers.reasoning import OpenAIReasoningConfig, OpenAIReasoningProvider
from voicenote.providers.transcription import (
    LocalWhisperConfig,
    LocalWhisperProvider,
    OpenAITranscriptionConfig,
    OpenAITranscriptionProvider,
)


def build_transcription_provider(config: VoiceNoteConfig) -> TranscriptionProvider:
    name = config.transcription_provider
    if name == "local_whisper":
        return LocalWhisperProvider(
            LocalWhisperConfig(
                model=config.transcription_model or "small",
                device=config.local_device,
                compute_type=config.local_compute_type,
                allow_model_download=config.allow_model_download,
            )
        )
    if name == "openai":
        return OpenAITranscriptionProvider(
            OpenAITranscriptionConfig(
                model=config.transcription_model or "whisper-1",
                allow_cloud_processing=config.allow_cloud_processing,
            )
        )
    if name is None:
        raise ProviderNotConfiguredError(
            "Choose a transcription provider explicitly: 'local_whisper' or 'openai'"
        )
    raise ProviderNotConfiguredError(f"Unknown transcription provider: {name!r}")


def build_correction_provider(config: VoiceNoteConfig) -> CorrectionProvider:
    name = config.correction_provider
    if name == "openai":
        return OpenAICorrectionProvider(
            OpenAICorrectionConfig(
                model=config.correction_model or "gpt-4o-mini",
                allow_cloud_processing=config.allow_cloud_processing,
            )
        )
    if name == "none":
        return NoOpCorrectionProvider()
    if name is None:
        raise ProviderNotConfiguredError(
            "Choose a correction provider explicitly: 'openai' or 'none'"
        )
    raise ProviderNotConfiguredError(f"Unknown correction provider: {name!r}")


def build_reasoning_provider(config: VoiceNoteConfig) -> ReasoningProvider:
    name = config.reasoning_provider
    if name == "openai":
        return OpenAIReasoningProvider(
            OpenAIReasoningConfig(
                model=config.reasoning_model or "gpt-4o-mini",
                allow_cloud_processing=config.allow_cloud_processing,
            )
        )
    if name is None:
        raise ProviderNotConfiguredError("Choose a reasoning provider explicitly: 'openai'")
    raise ProviderNotConfiguredError(f"Unknown reasoning provider: {name!r}")

