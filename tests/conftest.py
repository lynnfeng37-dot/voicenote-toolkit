from __future__ import annotations

from pathlib import Path

import pytest

from voicenote.core.schemas import AudioSource, ProviderMetadata, RawTranscript, TranscriptSegment


@pytest.fixture
def audio_source() -> AudioSource:
    return AudioSource(
        path="meeting.wav",
        media_type="audio/wav",
        sha256="0" * 64,
        size_bytes=100,
    )


@pytest.fixture
def raw_transcript(audio_source: AudioSource) -> RawTranscript:
    return RawTranscript(
        audio=audio_source,
        segments=(
            TranscriptSegment(
                id="seg-1",
                text="我们讨论夏普币率和百分之十的回报。",
                start_seconds=0,
                end_seconds=3.5,
                speaker="S1",
                language="zh",
            ),
        ),
        provider=ProviderMetadata(provider="fixture", model="fixture-v1"),
        detected_languages=("zh",),
    )


@pytest.fixture
def audio_file(tmp_path: Path) -> Path:
    path = tmp_path / "meeting.wav"
    path.write_bytes(b"RIFF-fixture")
    return path

