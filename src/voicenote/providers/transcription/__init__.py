"""Built-in transcription provider adapters."""

from voicenote.providers.transcription.local_whisper import (
    LocalWhisperConfig,
    LocalWhisperProvider,
)
from voicenote.providers.transcription.openai import (
    OpenAITranscriptionConfig,
    OpenAITranscriptionProvider,
)

__all__ = [
    "LocalWhisperConfig",
    "LocalWhisperProvider",
    "OpenAITranscriptionConfig",
    "OpenAITranscriptionProvider",
]

