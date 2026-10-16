from __future__ import annotations

import pytest

from voicenote.config import VoiceNoteConfig
from voicenote.exceptions import ProviderNotConfiguredError
from voicenote.providers.correction import OpenAICorrectionProvider
from voicenote.providers.factory import (
    build_correction_provider,
    build_reasoning_provider,
    build_transcription_provider,
)
from voicenote.providers.reasoning import OpenAIReasoningProvider
from voicenote.providers.transcription import LocalWhisperProvider, OpenAITranscriptionProvider


def test_factory_requires_explicit_provider_choice() -> None:
    with pytest.raises(ProviderNotConfiguredError, match="Choose"):
        build_transcription_provider(VoiceNoteConfig())


def test_factory_builds_local_provider_without_loading_model() -> None:
    provider = build_transcription_provider(
        VoiceNoteConfig(
            transcription_provider="local_whisper",
            transcription_model="medium",
            allow_model_download=True,
        )
    )

    assert isinstance(provider, LocalWhisperProvider)
    assert provider.config.model == "medium"
    assert provider.config.allow_model_download is True


def test_factory_preserves_openai_cloud_consent() -> None:
    provider = build_transcription_provider(
        VoiceNoteConfig(
            transcription_provider="openai",
            transcription_model="whisper-1",
            allow_cloud_processing=False,
        )
    )

    assert isinstance(provider, OpenAITranscriptionProvider)
    assert provider.config.allow_cloud_processing is False


def test_factory_builds_openai_correction_provider() -> None:
    provider = build_correction_provider(
        VoiceNoteConfig(
            correction_provider="openai",
            correction_model="gpt-4o-mini",
            allow_cloud_processing=True,
        )
    )

    assert isinstance(provider, OpenAICorrectionProvider)
    assert provider.config.model == "gpt-4o-mini"


def test_factory_builds_openai_reasoning_provider() -> None:
    provider = build_reasoning_provider(VoiceNoteConfig(
        reasoning_provider="openai", reasoning_model="gpt-4o-mini",
        allow_cloud_processing=True,
    ))
    assert isinstance(provider, OpenAIReasoningProvider)
    assert provider.config.allow_cloud_processing is True

