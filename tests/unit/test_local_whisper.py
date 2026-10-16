from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from voicenote.core.audio import prepare_audio
from voicenote.exceptions import ProviderError
from voicenote.providers.base import TranscriptionOptions
from voicenote.providers.transcription.local_whisper import (
    LocalWhisperConfig,
    LocalWhisperProvider,
)


class FakeWhisperModel:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def transcribe(self, audio: str, **kwargs: Any) -> tuple[list[Any], Any]:
        self.requests.append((audio, kwargs))
        segments = [
            SimpleNamespace(
                id=1,
                text=" 保留原始空格",
                start=0.5,
                end=2.0,
                avg_logprob=-0.2,
                compression_ratio=1.1,
                no_speech_prob=0.02,
            )
        ]
        info = SimpleNamespace(language="zh", language_probability=0.99, duration=2.0)
        return segments, info


def test_local_provider_is_lazy_and_disables_download_by_default(audio_file: Path) -> None:
    model = FakeWhisperModel()
    factory_calls: list[tuple[str, dict[str, Any]]] = []

    def factory(model_name: str, **kwargs: Any) -> FakeWhisperModel:
        factory_calls.append((model_name, kwargs))
        return model

    provider = LocalWhisperProvider(model_factory=factory)
    assert factory_calls == []

    result = provider.transcribe(
        prepare_audio(audio_file),
        TranscriptionOptions(prompt_terms=("夏普比率",)),
    )

    assert factory_calls[0][0] == "small"
    assert factory_calls[0][1]["local_files_only"] is True
    assert result.segments[0].text == " 保留原始空格"
    assert result.segments[0].start_seconds == 0.5
    assert model.requests[0][1]["hotwords"] == "夏普比率"


def test_local_model_download_requires_explicit_configuration(audio_file: Path) -> None:
    calls: list[dict[str, Any]] = []

    def factory(model_name: str, **kwargs: Any) -> FakeWhisperModel:
        del model_name
        calls.append(kwargs)
        return FakeWhisperModel()

    provider = LocalWhisperProvider(
        LocalWhisperConfig(allow_model_download=True),
        model_factory=factory,
    )
    provider.transcribe(prepare_audio(audio_file), TranscriptionOptions())

    assert calls[0]["local_files_only"] is False


def test_local_provider_rejects_diarization(audio_file: Path) -> None:
    provider = LocalWhisperProvider(model_factory=lambda *args, **kwargs: FakeWhisperModel())

    with pytest.raises(ProviderError, match="does not provide speaker diarization"):
        provider.transcribe(prepare_audio(audio_file), TranscriptionOptions(diarization=True))

