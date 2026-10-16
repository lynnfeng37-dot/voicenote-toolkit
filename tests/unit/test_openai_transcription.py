from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from voicenote.core.audio import prepare_audio
from voicenote.core.schemas import AudioSource
from voicenote.exceptions import CloudProcessingDisabledError, ProviderError
from voicenote.providers.base import TranscriptionOptions
from voicenote.providers.transcription.openai import (
    OpenAITranscriptionConfig,
    OpenAITranscriptionProvider,
)


class FakeTranscriptions:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> dict[str, Any]:
        self.requests.append(kwargs)
        return self.response


class FakeAudio:
    def __init__(self, transcriptions: FakeTranscriptions) -> None:
        self.transcriptions = transcriptions


class FakeClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self.transcriptions = FakeTranscriptions(response)
        self.audio = FakeAudio(self.transcriptions)


def test_cloud_provider_fails_before_opening_file_without_consent(
    audio_source: AudioSource,
) -> None:
    provider = OpenAITranscriptionProvider(client=FakeClient({"text": "unused"}))

    with pytest.raises(CloudProcessingDisabledError):
        provider.transcribe(audio_source, TranscriptionOptions())


def test_whisper_verbose_segments_are_mapped_without_rewriting(audio_file: Path) -> None:
    client = FakeClient(
        {
            "text": " Raw text",
            "language": "chinese",
            "segments": [
                {
                    "id": 7,
                    "start": 1.25,
                    "end": 3.5,
                    "text": " Raw text",
                    "avg_logprob": -0.25,
                    "no_speech_prob": 0.01,
                }
            ],
        }
    )
    provider = OpenAITranscriptionProvider(
        OpenAITranscriptionConfig(allow_cloud_processing=True),
        client=client,
    )

    result = provider.transcribe(
        prepare_audio(audio_file),
        TranscriptionOptions(language="zh", prompt_terms=("夏普比率",)),
    )

    assert result.segments[0].text == " Raw text"
    assert result.segments[0].start_seconds == 1.25
    assert result.segments[0].provider_metadata["avg_logprob"] == -0.25
    request = client.transcriptions.requests[0]
    assert request["model"] == "whisper-1"
    assert request["response_format"] == "verbose_json"
    assert request["timestamp_granularities"] == ["segment"]
    assert request["prompt"] == "夏普比率"


def test_diarization_uses_speaker_response_and_omits_prompt(audio_file: Path) -> None:
    client = FakeClient(
        {
            "text": "Hello",
            "segments": [
                {"id": "seg_001", "start": 0, "end": 1, "text": "Hello", "speaker": "A"}
            ],
        }
    )
    provider = OpenAITranscriptionProvider(
        OpenAITranscriptionConfig(allow_cloud_processing=True),
        client=client,
    )

    result = provider.transcribe(
        prepare_audio(audio_file),
        TranscriptionOptions(diarization=True, prompt_terms=("ignored",)),
    )

    assert result.segments[0].speaker == "A"
    request = client.transcriptions.requests[0]
    assert request["model"] == "gpt-4o-transcribe-diarize"
    assert request["response_format"] == "diarized_json"
    assert request["chunking_strategy"] == "auto"
    assert "prompt" not in request


def test_oversized_file_is_rejected_before_client_call(audio_source: AudioSource) -> None:
    client = FakeClient({"text": "unused"})
    provider = OpenAITranscriptionProvider(
        OpenAITranscriptionConfig(allow_cloud_processing=True, max_file_bytes=10),
        client=client,
    )

    with pytest.raises(ProviderError, match="exceeds"):
        provider.transcribe(audio_source, TranscriptionOptions())
    assert client.transcriptions.requests == []

